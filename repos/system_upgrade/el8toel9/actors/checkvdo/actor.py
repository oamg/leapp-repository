from leapp.actors import Actor
from leapp.libraries.actor.checkvdo import check_vdo
from leapp.models import VdoConversionInfo, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVdo(Actor):
    """
    Check if VDO devices need to be migrated to lvm management.

    `Background`
    ============
    In RHEL 9.0 the indepdent VDO management software, `vdo manager`, is
    superseded by LVM management.  Existing VDOs must be converted to LVM-based
    management *before* upgrading to RHEL 9.0.

    The `CheckVdo` actor provides a pre-upgrade check for VDO devices that have
    not been converted and, if any are found, produces an inhibitory report
    during upgrade check phase.   If none are found `CheckVdo` does not produce
    a report concerning such VDO devices.

    As there currently exists the theoretical possibility that a VDO device may
    not complete its conversion to LVM-based management (e.g., via a poorly
    timed system crash during the conversion) `CheckVdo` also provides a
    pre-upgrade check for VDO devices in this state.  If any are found
    `CheckVdo` produces an inhibitory report during upgrade check phase.  If
    none are found `CheckVdo` does not produce a report concerning such VDO
    devices.
    """

    name = 'check_vdo'
    consumes = (VdoConversionInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for conversion_info in self.consume(VdoConversionInfo):
            self.produce(check_vdo(conversion_info))
