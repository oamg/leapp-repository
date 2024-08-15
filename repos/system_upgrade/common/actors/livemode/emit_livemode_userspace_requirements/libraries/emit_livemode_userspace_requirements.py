from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig, TargetUserSpaceUpgradeTasks

# NOTE: would also need
# _REQUIRED_PACKAGES from actors/commonleappdracutmodules/libraries/modscan.py

_REQUIRED_PACKAGES_FOR_LIVE_MODE = [
    'systemd-container',
    'dbus-daemon',
    'NetworkManager',
    'util-linux',
    'dracut-live',
    'dracut-squash',
    'dmidecode',
    'pciutils',
    'lsscsi',
    'passwd',
    'kexec-tools',
    'vi',
    'less',
    'openssh-clients',
    'strace',
    'tcpdump',
]


def emit_livemode_userspace_requirements():
    livemode_config = next(api.consume(LiveModeConfig), None)
    if not livemode_config or not livemode_config.is_enabled:
        return

    packages = _REQUIRED_PACKAGES_FOR_LIVE_MODE + livemode_config.additional_packages
    if livemode_config.setup_opensshd_with_auth_keys:
        packages += ['openssh-server', 'crypto-policies']

    packages = sorted(set(packages))

    api.produce(TargetUserSpaceUpgradeTasks(install_rpms=packages))
