from leapp.actors import Actor
from leapp.libraries.actor import checkvalidgrubcfghybrid
from leapp.models import FirmwareFacts, HybridImageAzure
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckValidGrubConfigHybrid(Actor):
    """
    Check potential for boot failures in Azure Gen1 VMs due to invalid grubcfg

    This actor addresses the issue where the `/boot/grub2/grub.cfg` file is
    overwritten during the upgrade process by an old RHEL7 configuration
    leftover on the system, causing the system to fail to boot.

    The problem occurs on hybrid Azure images, which support both UEFI and
    Legacy systems. The issue is caused by one of the scriplets in `grub-efi`
    which overwrites during the upgrade current configuration in
    `/boot/grub2/grub.cfg` by an old configuration from
    `/boot/efi/EFI/redhat/grub.cfg`.

    The issue is detected specifically to Azure hybrid cloud systems.

    """

    name = 'check_valid_grubcfg_hybrid'
    consumes = (FirmwareFacts, HybridImageAzure,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkvalidgrubcfghybrid.process()
