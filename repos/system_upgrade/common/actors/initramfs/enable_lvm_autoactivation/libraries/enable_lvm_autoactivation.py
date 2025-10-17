from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, LiveModeConfig, UpgradeInitramfsTasks


def emit_lvm_autoactivation_instructions():
    livemode_config = next(api.consume(LiveModeConfig), None)
    if livemode_config and livemode_config.is_enabled:
        api.current_logger().debug(
            'Skipping LVM autoactivation instructions production due to livemode being enabled.'
        )
        return

    if not has_package(DistributionSignedRPM, 'lvm2'):
        api.current_logger().debug(
            'Upgrade initramfs will not autoenable LVM devices - `lvm2` RPM is not installed.'
        )
        return

    # the 69-dm-lvm.rules trigger pvscan and vgchange when LVM device is detected
    files_to_include = [
        '/usr/sbin/pvscan',
        '/usr/sbin/vgchange',
        '/usr/lib/udev/rules.d/69-dm-lvm.rules'
    ]
    lvm_autoactivation_instructions = UpgradeInitramfsTasks(include_files=files_to_include)

    api.produce(lvm_autoactivation_instructions)
