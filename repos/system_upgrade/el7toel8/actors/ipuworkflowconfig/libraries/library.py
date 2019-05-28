import os

from leapp.models import EnvVar


ENV_IGNORE = ('LEAPP_CURRENT_PHASE', 'LEAPP_CURRENT_ACTOR')


def get_env_vars():
    """
    Gather LEAPP_DEVEL environment variables and provide them as messages to be
    available after reboot.
    """
    return [EnvVar(name=k, value=v) for (k, v) in os.environ.items() if k.startswith('LEAPP_') and k not in ENV_IGNORE]
