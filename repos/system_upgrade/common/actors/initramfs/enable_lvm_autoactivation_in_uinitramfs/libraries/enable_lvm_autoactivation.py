from leapp.libraries.stdlib import api
from leapp.models import UpgradeInitramfsTasks

def emit_lvm_autoactivation_instructions():
    files_to_include = [
        '/usr/sbin/pvscan',
        '/usr/sbin/vgchange',
        '/usr/lib/udev/rules.d/69-dm-lvm.rules'  # Rule that triggers pvscan and vgchange when LVM device is detected
    ]
    lvm_autoactivation_instructions = UpgradeInitramfsTasks(include_files=files_to_include)

    api.produce(lvm_autoactivation_instructions)
