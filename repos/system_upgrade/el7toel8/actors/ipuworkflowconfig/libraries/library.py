import os

from leapp.libraries.common import reporting
from leapp.models import EnvVar, OSRelease

CURRENT_TARGET_VERSION = '8.0'

ENV_IGNORE = ('LEAPP_CURRENT_PHASE', 'LEAPP_CURRENT_ACTOR', 'LEAPP_VERBOSE',
              'LEAPP_DEBUG')


def get_env_vars():
    """
    Gather LEAPP_DEVEL environment variables and provide them as messages to be
    available after reboot.
    """
    return [EnvVar(name=k, value=v) for (k, v) in os.environ.items() if k.startswith('LEAPP_') and k not in ENV_IGNORE]


def get_os_release(path):
    """Retrieve data about System OS release from provided file."""
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
            return OSRelease(
                release_id=data.get('ID', '').strip('"'),
                name=data.get('NAME', '').strip('"'),
                pretty_name=data.get('PRETTY_NAME', '').strip('"'),
                version=data.get('VERSION', '').strip('"'),
                version_id=data.get('VERSION_ID', '').strip('"'),
                variant=data.get('VARIANT', '').strip('"') or None,
                variant_id=data.get('VARIANT_ID', '').strip('"') or None
            )
    except IOError as e:
        reporting.report_generic(
            title='Error while collecting system OS facts',
            summary=str(e),
            severity='high',
            flags=['inhibitor'])
        return None


def get_target_version():
    return os.getenv('LEAPP_DEVEL_TARGET_RELEASE', None) or CURRENT_TARGET_VERSION
