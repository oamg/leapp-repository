from leapp.actors import Actor
from leapp.libraries.common.reporting import report_generic
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.models import Authselect, AuthselectDecision
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ApplicationsPhaseTag, ExperimentalTag


class AuthselectApply(Actor):
    """
    Apply changes suggested by AuthselectScanner.

    If confirmed by admin in AuthselectDecision, call suggested authselect
    command to configure the system using this tool.
    """

    name = 'authselect_apply'
    consumes = (Authselect, AuthselectDecision,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ApplicationsPhaseTag, ExperimentalTag)

    def process(self):
        model = next(self.consume(Authselect))
        decision = next(self.consume(AuthselectDecision))

        if not decision.confirmed or model.profile is None:
            return

        command = ['authselect', 'select', '--force', model.profile] + model.features

        try:
            run(command)
        except CalledProcessError as err:
            report_generic(
                title='Authselect call failed.',
                summary=str(err)
            )
            return

        report_generic(
            title='System was converted to authselect.',
            summary='System was converted to authselect with the '
                    'following call: "{}"'.format(' '.join(command))
        )
