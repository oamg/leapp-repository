from leapp.actors import Actor
from leapp.libraries.actor import blsgrubcfgonppc64
from leapp.models import DefaultGrubInfo, FirmwareFacts, GrubCfgBios, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBlsGrubOnPpc64(Actor):
    """
    Check whether GRUB config is BLS aware on RHEL 8 ppc64le systems

    After a ppc64 system is upgraded from RHEL 8 to RHEL 9 and
    GRUB config on RHEL 8 is not yet BLS aware, the system boots
    into el8 kernel because the config is not successfully migrated by
    GRUB during the upgrade process.

    IMPORTANT NOTE: The later fix which is based on the outcome of this
    actor is applied only for virtualized ppc64le systems as we got
    unexpected behavior on bare metal ppc64le systems which needs to be
    investigated first.

    """

    name = 'check_bls_grub_onppc64'
    consumes = (DefaultGrubInfo, GrubCfgBios, FirmwareFacts)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        blsgrubcfgonppc64.process()
