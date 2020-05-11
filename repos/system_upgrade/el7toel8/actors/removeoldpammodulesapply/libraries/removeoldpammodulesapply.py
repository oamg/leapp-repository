import os
import re


def read_file(config):
    """
        Read file contents. Return empty string if the file does not exist.
    """
    if not os.path.isfile(config):
        return ""
    with open(config) as f:
        return f.read()


def comment_modules(modules, content):
    """
    Disable modules in file content by commenting them.
    """
    for module in modules:
        content = re.sub(
            r'^([ \t]*[^#\s]+.*{0}\.so.*)$'.format(module),
            r'#\1',
            content,
            flags=re.MULTILINE
        )

    return content
