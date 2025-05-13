from leapp.actors import Actor
from leapp.libraries.actor import ensurevalidgrubcfghybrid
from leapp.models import HybridImageAzure
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class EnsureValidGrubcfgHybrid(Actor):
    """
    Resolve boot failures in Azure Gen1 VMs during upgrades from RHEL 7 to RHEL 8 to RHEL 9.

    If old configuration is detected, this actor regenerates the grub
    configuration using `grub2-mkconfig -o /boot/grub2/grub.cfg` after
    installing rpms to ensure the correct boot configuration is in place.

    Old configuration is detected by looking for a menuentry corresponding to a
    kernel from RHEL 7 which should not be present on RHEL 8 systems.

    The fix is applied specifically to Azure hybrid cloud systems.

    See also CheckValidGrubConfigHybrid actor.

    """

    name = 'ensure_valid_grubcfg_hybrid'
    consumes = (HybridImageAzure,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        ensurevalidgrubcfghybrid.process()
