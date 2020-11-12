from leapp.actors import Actor
from leapp.dialogs import Dialog
from leapp.dialogs.components import BooleanComponent
from leapp.models import Authselect, AuthselectDecision
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


resources = [
    reporting.RelatedResource('package', 'authselect'),
    reporting.RelatedResource('package', 'authconfig'),
    reporting.RelatedResource('file', '/etc/nsswitch.conf')
]


class AuthselectCheck(Actor):
    """
    Confirm suggested authselect call from AuthselectScanner.

    AuthselectScanner produces an Authselect model that contains changes
    that are suggested based on current configuration. This actor will
    ask administrator for confirmation and will report the result.
    """

    name = 'authselect_check'
    consumes = (Authselect,)
    produces = (AuthselectDecision, Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)
    dialogs = (
        Dialog(
            scope='authselect_check',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='confirm',
                    label='Configure PAM and nsswitch.conf with the following '
                          'authselect call?',
                    default=True,
                    description='If yes, suggested authselect profile will '
                                'be applied on your system to generate '
                                'PAM and nsswitch.conf configuration. '
                                'If no, current configuration will be kept '
                                'intact.',
                    reason='There is a new tool called authselect in RHEL8 '
                           'that replaced authconfig which is used to manage '
                           'authentication (PAM) and identity (nsswitch.conf) '
                           'sources. It is recommended to switch to this tool.'
                ),
            )
        ),
    )

    def process(self):
        model = next(self.consume(Authselect))

        # If there is no equivalent authselect profile we will not touch
        # the current configuration. Therefore there is no need for
        # confirmation.
        if model.profile is None:
            self.produce_current_configuration(model)
            return

        command = 'authselect select {0} {1} --force'.format(
            model.profile,
            ' '.join(model.features)
        )

        # We do not need admin confirmation if the current
        # configuration was generated with authconfig.
        if not model.confirm:
            self.produce_authconfig_configuration(model, command)
            return

        # Authselect profile is available but we require confirmation.
        confirmed = self.get_confirmation(model, command)
        if confirmed is not None:
            # A user has made his choice
            self.produce_suggested_configuration(model, confirmed, command)

    def get_confirmation(self, model, command):
        dialog = self.dialogs[0]

        dialog.components[0].label += "\n{}\n".format(command)

        return self.get_answers(dialog).get('confirm')

    def produce_authconfig_configuration(self, model, command):
        self.produce(
            AuthselectDecision(
                confirmed=True
            )
        )

        create_report([
            reporting.Title(
                'Authselect will be used to configure PAM and nsswitch.conf.'
            ),
            reporting.Summary(
                'There is a new tool called authselect in RHEL8 that '
                'replaced authconfig. The upgrade process detected '
                'that authconfig was used to generate current '
                'configuration and it will automatically convert it '
                'to authselect. Authselect call is: {}. The process will '
                'also enable "oddjobd" systemd service on startup'.format(command)
            ),
            reporting.Groups([
                reporting.Groups.AUTHENTICATION,
                reporting.Groups.SECURITY,
                reporting.Groups.TOOLS
            ])
        ] + resources)

    def produce_current_configuration(self, model):
        self.produce(
            AuthselectDecision(
                confirmed=False
            )
        )

        create_report([
            reporting.Title(
                'Current PAM and nsswitch.conf configuration will be kept.'
            ),
            reporting.Summary(
                'There is a new tool called authselect in RHEL8 that '
                'replaced authconfig. The upgrade process was unable '
                'to find an authselect profile that would be equivalent '
                'to your current configuration. Therefore your '
                'configuration will be left intact.'
            ),
            reporting.Groups([
                reporting.Groups.AUTHENTICATION,
                reporting.Groups.SECURITY,
                reporting.Groups.TOOLS
            ]),
            reporting.Severity(reporting.Severity.INFO)
        ] + resources)

    def produce_suggested_configuration(self, model, confirmed, command):
        self.produce(
            AuthselectDecision(
                confirmed=confirmed
            )
        )
        if confirmed:
            create_report([
                reporting.Title(
                    'Authselect will be used to configure PAM and nsswitch.conf.'
                ),
                reporting.Summary(
                    'There is a new tool called authselect in RHEL8 that '
                    'replaced authconfig. The upgrade process suggested '
                    'an authselect profile that is similar to your '
                    'current configuration and your system will be switched '
                    'to this profile. Authselect call is: {}. The process will '
                    'also enable "oddjobd" systemd service on startup'.format(command)
                ),
                reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS
                ])
            ] + resources)

        else:
            create_report([
                reporting.Title(
                    'Current PAM and nsswitch.conf configuration will be kept.'
                ),
                reporting.Summary(
                    'There is a new tool called authselect in RHEL8 that '
                    'replaced authconfig. The upgrade process suggested '
                    'an authselect profile that is similar to your '
                    'current configuration. However this suggestion was '
                    'refused therefore existing configuration will be kept '
                    'intact.',
                ),
                reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS
                ]),
                reporting.Remediation(commands=[[command]]),
                reporting.Severity(reporting.Severity.MEDIUM)
            ] + resources)
