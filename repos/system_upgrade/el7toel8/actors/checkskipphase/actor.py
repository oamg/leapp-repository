from leapp.actors import Actor
from leapp.messaging.commands import SkipPhasesUntilCommand
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckSkipPhase(Actor):
    """
    Skip all the subsequent phases until the report phase.

    The phases that follow after the Checks phase work with the target (RHEL 8)
    user space - stuff around preparing and checking the rpm transaction.
    We do not want to process those phases in case of inhibition - e.g. for
    a specific HW unsupported by the target system we cannot do anything - we
    can just see some unclear errors in such case. So we want to instead skip
    to the Reports phase to provide clear report to user without confusing
    errors.

    The actor is processed after all actors in the phase (that provides Report
    messages) are processed.
    """

    name = 'check_skip_phase'
    consumes = (Report,)
    produces = ()
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        results = list(self.consume(Report))
        inhibitors = [msg for msg in results if 'inhibitor' in msg.report.get('flags', [])]
        if inhibitors:
            self.log.info("An upgrade inhibitor detected. Skipping to the Report phase.")
            # until_phase='targettransactioncheck'  === phase after this phase will be processed
            # === the Reports phase
            self._messaging.command(SkipPhasesUntilCommand(until_phase='targettransactioncheck'))
