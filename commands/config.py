from leapp import config


def get_config():
    if not config._LEAPP_CONFIG:
        config._CONFIG_DEFAULTS['repositories'] = {'repo_path': '/etc/leapp/repos.d'}
    return config.get_config()
