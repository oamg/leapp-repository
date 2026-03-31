from leapp.actors import Actor
from leapp.libraries.actor import regenerategrubcfg
from leapp.models import DefaultGrubInfo, TransactionCompleted
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class RegenerateGrubCfg(Actor):
    """
    Regenerate GRUB2 configuration during conversion from EL8 to EL9.

    During distribution conversions (e.g. CentOS to RHEL), the GRUB2
    configuration may need to be regenerated to ensure compatibility
    with the target distribution's GRUB2 tooling. This actor runs
    grub2-mkconfig when BLS is enabled in /etc/default/grub.
    """

    name = 'regenerate_grub_cfg'
    consumes = (DefaultGrubInfo, TransactionCompleted)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        regenerategrubcfg.process()
