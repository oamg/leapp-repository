from leapp.actors import Actor
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.models import Authselect, AuthselectDecision
from leapp import reporting
from leapp.reporting import Report, create_report
from leapp.tags import IPUWorkflowTag, ApplicationsPhaseTag


resources = [
    reporting.RelatedResource('package', 'authselect'),
    reporting.RelatedResource('package', 'authconfig'),
    reporting.RelatedResource('file', '/etc/nsswitch.conf')
]


class AuthselectApply(Actor):
    """
    Apply changes suggested by AuthselectScanner.

    If confirmed by admin in AuthselectDecision, call suggested authselect
    command to configure the system using this tool.
    """

    name = 'authselect_apply'
    consumes = (Authselect, AuthselectDecision,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        model = next(self.consume(Authselect))
        decision = next(self.consume(AuthselectDecision))

        if not decision.confirmed or model.profile is None:
            return

        command = ['authselect', 'select', '--force', model.profile] + model.features

        try:
            run(command)
        except CalledProcessError as err:
            create_report([  # pylint: disable-msg=too-many-arguments
                reporting.Title('Authselect call failed'),
                reporting.Summary(str(err)),
                reporting.Severity(reporting.Severity.MEDIUM),
                reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS,
                    reporting.Groups.FAILURE
                ]),
            ] + resources)  # pylint: disable-msg=too-many-arguments
            return

        try:
            run(['systemctl', 'enable', 'oddjobd.service'])
        except (OSError, CalledProcessError) as e:
            self.log.warning('Error enabling oddjobd.service: {}'.format(e))

        create_report([  # pylint: disable-msg=too-many-arguments
            reporting.Title('System was converted to authselect.'),
            reporting.Summary(
                'System was converted to authselect with the '
                'following call: "{}"'.format(' '.join(command))
            ),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS
                ])
        ] + resources)  # pylint: disable-msg=too-many-arguments
