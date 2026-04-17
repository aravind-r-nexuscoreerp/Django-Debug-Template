import os
import re
import hashlib
from django.conf import settings
from django.template.loaders.base import Loader as BaseLoader
from django.template import TemplateDoesNotExist


class DebugLoader(BaseLoader):
    def __init__(self, engine, loaders):
        self.engine = engine
        self.loaders = engine.get_template_loaders(loaders)

    def get_contents(self, origin):
        try:
            for loader in self.loaders:
                try:
                    contents = loader.get_contents(origin)
                    if not settings.SHOW_TEMPLATE_DEBUG:
                        return contents

                    # Skip debug wrapping for admin templates
                    if self.is_admin_template(origin.template_name):
                        return contents

                    return self.debug_wrap(contents, origin.template_name)
                except TemplateDoesNotExist:
                    continue
            raise TemplateDoesNotExist(origin, backend=self.engine)
        except AttributeError:
            pass
        return super().get_contents(origin)

    def get_template_sources(self, template_name):
        for loader in self.loaders:
            yield from loader.get_template_sources(template_name)

    def is_admin_template(self, template_name):
        """
        Check if the template is from Django admin.
        Returns True if it's an admin template that should be excluded.
        """
        admin_patterns = [
            "admin/",  # Django admin templates
            "django/contrib/admin/",  # Full path to admin templates
        ]

        return any(pattern in template_name for pattern in admin_patterns)

    def debug_wrap(self, content, template_name):
        # Generate a color based on the filename hash
        hash_object = hashlib.md5(template_name.encode())
        hex_dig = hash_object.hexdigest()
        color = f"#{hex_dig[:6]}"

        # Styles for the debug box
        style = (
            f"border: 2px solid {color}; "
            "padding: 5px; "
            "margin: 5px; "
            "position: relative; "
            "display: block;"
        )
        label_style = (
            f"background-color: {color}; "
            "color: #fff; "
            "padding: 2px 5px; "
            "font-size: 10px; "
            "position: absolute; "
            "top: -10px; "
            "left: 10px; "
            "z-index: 1000;"
            "font-family: monospace;"
        )

        label_html = (
            f'<div class="debug-label" style="{label_style}">{template_name}</div>'
        )

        # Check if the template extends another template
        # We need a more robust check for 'extends' which must be the first tag
        # We can strip leading whitespace/comments first to check?
        # Actually Django parser handles comments before extends.
        # But for regex simplicity, let's just look for it early on.

        if re.search(r"^\s*{%\s*extends", content):
            # If extending, we wrap contents of blocks.

            def wrap_block_start(match):
                block_tag = match.group(1)
                return f'{block_tag}<div style="{style}">{label_html}'

            # Replace start block
            # This regex captures the opening block tag
            content = re.sub(r"({%\s*block\s+\w+\s*%})", wrap_block_start, content)

            # Replace end block with closing div BEFORE the endblock tag
            # Because we opened the div right after the start block tag.
            content = re.sub(r"({%\s*endblock(?: .*)?\s*%})", r"</div>\1", content)

            return content
        else:
            # If not extending, wrap the whole thing
            return f'<div style="{style}">{label_html}{content}</div>'




# settings.py
# APP_DIRS = False
# module_name.file_name.class -> erp_backend.template_loader.DebugLoader
SHOW_TEMPLATE_DEBUG = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                ('erp_backend.template_loader.DebugLoader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]
