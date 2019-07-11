from leapp.libraries.stdlib import api


def get_env(name, default=None):
    """ Return Leapp environment variable value if matched by name """
    for var in api.current_actor().configuration.leapp_env_vars:
        if var.name == name:
            return var.value
    return default


def get_all_envs():
    """ Return all Leapp environment variables (both name and value) """
    return api.current_actor().configuration.leapp_env_vars
