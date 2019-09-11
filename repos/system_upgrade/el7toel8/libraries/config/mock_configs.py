from leapp.models import IPUConfig, EnvVar, OSRelease, Version

CONFIG = IPUConfig(
    leapp_env_vars=[EnvVar(name='LEAPP_DEVEL', value='0')],
    os_release=OSRelease(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='RHEL',
        version='7.6 (Maipo)',
        version_id='7.6'
    ),
    version=Version(
        source='7.6',
        target='8.0'
    ),
    architecture='x86_64'
)

CONFIG_ALL_SIGNED = IPUConfig(
    leapp_env_vars=[EnvVar(name='LEAPP_DEVEL_RPMS_ALL_SIGNED', value='1')],
    os_release=OSRelease(
        release_id='rhel',
        name='Red Hat Enterprise Linux Server',
        pretty_name='RHEL',
        version='7.6 (Maipo)',
        version_id='7.6'
    ),
    version=Version(
        source='7.6',
        target='8.0'
    ),
    architecture='x86_64'
)
