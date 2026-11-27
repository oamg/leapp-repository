from leapp.libraries.stdlib import api
from leapp.models import LiveModeConfig, TargetUserSpaceUpgradeTasks

# NOTE: would also need
# _REQUIRED_PACKAGES from actors/commonleappdracutmodules/libraries/modscan.py

# Notes about the required packages:
# - device-mapper-multipath: we require the package unconditionally, regardless
# # of whether the system is using multipath. As the package is small, this is
# # the simplest solution to mount multipath in the live system (the necessary
# # changes to userspace are already performed by other multipath-related actors).
# # No harm is done if the system does not use multipath (no drives will be
# # collected under a single multipath drive). However, there are setups that do
# # not use multipath, but the systems has multiple paths to the same disk. Such
# # setups cause us to fail to mount storage due to XFS seeing disks with the same
# # UUIDs. Having multipath is actually helpful there, as we create temporary multipath
# # for upgrade purposes (the target system will not have the multipath).
_REQUIRED_PACKAGES_FOR_LIVE_MODE = [
    'systemd-container',
    'dbus-daemon',
    'device-mapper-multipath',
    'NetworkManager',
    'util-linux',
    'dracut-live',
    'dracut-squash',
    'passwd',
    'kexec-tools',
    'less',
    'openssh-clients',
]


def emit_livemode_userspace_requirements():
    livemode_config = next(api.consume(LiveModeConfig), None)
    if not livemode_config or not livemode_config.is_enabled:
        return

    packages = _REQUIRED_PACKAGES_FOR_LIVE_MODE + livemode_config.additional_packages
    if livemode_config.setup_opensshd_with_auth_keys:
        packages += ['openssh-server', 'crypto-policies']

    if livemode_config.capture_upgrade_strace_into:
        packages += ['strace']

    packages = sorted(set(packages))

    api.produce(TargetUserSpaceUpgradeTasks(install_rpms=packages))
