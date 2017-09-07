import sys

from leapp.actors import Actor
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag
from leapp.models import SelinuxPermissiveDecision, FinalReport
from leapp.libraries.actor.setpermissiveselinux import selinux_set_permissive


class SetPermissiveSelinux(Actor):
    name = 'set_permissive_se_linux'
    description = 'Set SElinux into permissive mode if it was in enforcing mode'
    consumes = (SelinuxPermissiveDecision,)
    produces = (FinalReport,)
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        for decision in self.consume(SelinuxPermissiveDecision):
            if decision.set_permissive:
                success, err_msg = selinux_set_permissive()
                if not success:
                    self.produce(FinalReport(
                        severity='Error',
                        result='Fail',
                        summary='Could not set SElinux into permissive mode',
                        details=err_msg,))
                    self.log.critical('Could not set SElinux into permissive mode: %s' % err_msg)
