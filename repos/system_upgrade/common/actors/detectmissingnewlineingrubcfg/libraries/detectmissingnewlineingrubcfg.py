import os


def _get_config_contents(config_path):
    if os.path.isfile(config_path):
        with open(config_path, 'r') as config:
            return config.read()
    return ''


def is_grub_config_missing_final_newline(conf_file):
    config_contents = _get_config_contents(conf_file)
    return config_contents != '' and config_contents[-1] != '\n'
