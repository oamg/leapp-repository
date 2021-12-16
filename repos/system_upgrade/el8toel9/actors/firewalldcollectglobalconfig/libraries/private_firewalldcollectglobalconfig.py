import os

from leapp.models import FirewalldGlobalConfig


def read_config():
    default_conf = FirewalldGlobalConfig()

    path = '/etc/firewalld/firewalld.conf'
    if not os.path.exists(path):
        return default_conf

    conf_dict = {}
    with open(path) as conf_file:
        for line in conf_file:
            (key, _unused, value) = line.partition('=')
            if not value:
                continue

            value = value.lower().strip()
            if value in ['yes', 'true']:
                value = True
            if value in ['no', 'false']:
                value = False

            # Only worry about config used by our Model
            key = key.lower().strip()
            if hasattr(default_conf, key):
                conf_dict[key] = value

    return FirewalldGlobalConfig(**conf_dict)
