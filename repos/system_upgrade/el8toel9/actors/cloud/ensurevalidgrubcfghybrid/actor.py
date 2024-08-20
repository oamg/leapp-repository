from leapp.actors import Actor
from leapp.libraries.actor import ensurevalidgrubcfghybrid
from leapp.models import HybridImage
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class EnsureValidGrubcfgHybrid(Actor):
    """
    Resolve boot failures in Azure Gen1 VMs during upgrades from RHEL 7 to RHEL 8 to RHEL 9.

    This actor addresses the issue where the `/boot/grub2/grub.cfg` file is
    overwritten during the upgrade process by an old RHEL7 configuration
    leftover on the system, causing the system to fail to boot.

    The problem occurs on hybrid Azure images, which support both UEFI and
    Legacy systems and have both `grub-pc` and `grub-efi` packages installed.
    It is caused by one of the scriplets in `grub-efi` which overwrites the old
    configuration.

    If old configuration is detected, this actor regenerates the grub
    configuration using `grub2-mkconfig -o /boot/grub2/grub.cfg` after
    installing rpms to ensure the correct boot configuration is in place.

    The fix is applied specifically to Azure hybrid cloud systems.

    """

    name = 'ensure_valid_grubcfg_hybrid'
    consumes = (HybridImage,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        ensurevalidgrubcfghybrid.process()
