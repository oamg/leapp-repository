import re


def detect_config_error(conf_file):
    '''
    Check grub configuration for syntax error in GRUB_CMDLINE_LINUX value.

    :return: Function returns True if error was detected, otherwise False.
    '''
    with open(conf_file, 'r') as f:
        config = f.read()

    pattern = r'GRUB_CMDLINE_LINUX="[^"]+"(?!(\s*$)|(\s+(GRUB|#)))'
    return re.search(pattern, config) is not None
