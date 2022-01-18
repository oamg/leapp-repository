from leapp.actors import Actor
from leapp.libraries.actor import grub2mkconfigonppc64
from leapp.models import DefaultGrubInfo, FirmwareFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class Grub2MkconfigOnPpc64(Actor):
    """
    Regenerate Grub config after RHEL 8 to RHEL 9 rpm transaction

    Actor runs 'grub2-mkconfig' to regenerate Grub config after RHEL 8 to RHEL 9
    rpm transaction in case system is running on ppc64le, GRUB_ENABLE_BLSCFG=true
    and '/boot/grub2/grub.cfg' config file does not yet work with BLS entries.
    For the system to successfully boot into el9 kernel, it is essential that the
    grub config file is abvle to work with the BLS entries.

    IMPORTANT NOTE: The fix is applied only for virtualized ppc64le systems as we got
    unexpected behavior on bare metal ppc64le systems which needs to be
    investigated first.

    """

    name = 'grub2mkconfig_on_ppc64'
    consumes = (DefaultGrubInfo, FirmwareFacts)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        grub2mkconfigonppc64.process()
