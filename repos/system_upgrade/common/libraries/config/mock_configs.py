
"""
This is not regular library.

The library is supposed to be used only for testing purposes. Import of the
library is expected only inside test files.
"""

from leapp.models import EnvVar, IPUConfig, OSRelease, Version

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
    architecture='x86_64',
    kernel='3.10.0-957.43.1.el7.x86_64',
)

CONFIG_NO_NETWORK_RENAMING = IPUConfig(
    leapp_env_vars=[EnvVar(name='LEAPP_DEVEL', value='0'), EnvVar(name='LEAPP_NO_NETWORK_RENAMING', value='1')],
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
    architecture='x86_64',
    kernel='3.10.0-957.43.1.el7.x86_64',
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
    architecture='x86_64',
    kernel='3.10.0-957.43.1.el7.x86_64',
)

CONFIG_S390X = IPUConfig(
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
    architecture='s390x',
    kernel='3.10.0-957.43.1.el7.x86_64',
)
