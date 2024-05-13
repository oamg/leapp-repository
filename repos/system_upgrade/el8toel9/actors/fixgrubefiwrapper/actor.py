import os

from leapp.actors import Actor
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import FirmwareFacts, TransactionCompleted
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class FixGrubEFIWrapper(Actor):
    """
    Update /boot/efi/EFI/redhat/grub.cfg on UEFI systems.

    See [RHEL-36186](https://issues.redhat.com/browse/RHEL-36186).
    """

    name = 'fix_grub_efi_wrapper'
    consumes = (TransactionCompleted, FirmwareFacts)
    produces = (Report,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        ff = next(self.consume(FirmwareFacts), None)
        if not ff:
            api.current_logger().warning('Could not identify system firmware')
            return

        if ff.firmware == 'efi' and os.path.ismount('/boot/efi') and os.path.isfile('/boot/efi/EFI/redhat/grub.cfg'):
            api.current_logger().info('Removing --root-dev-only if present.')
            try:
                run(['/usr/bin/sed', '-i', r's/--root-dev-only\s*//', '/boot/efi/EFI/redhat/grub.cfg'])
            except (OSError, CalledProcessError):
                api.current_logger().warning('Cannot apply the fix of /boot/efi/EFI/redhat/grub.cfg.')
                return
            api.current_logger().info('Removed --root-dev-only if present.')
