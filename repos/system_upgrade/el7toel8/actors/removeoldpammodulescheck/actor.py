from leapp.actors import Actor
from leapp.dialogs import Dialog
from leapp.dialogs.components import BooleanComponent
from leapp.models import RemovedPAMModules
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class RemoveOldPAMModulesCheck(Actor):
    """
    Check if it is all right to disable PAM modules that are not in RHEL-8.

    If admin will refuse to disable these modules (pam_pkcs11 and pam_krb5),
    upgrade will be stopped. Otherwise we would risk locking out the system
    once these modules are removed.
    """
    name = 'removed_pam_modules_check'
    consumes = (RemovedPAMModules,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)
    dialogs = (
        Dialog(
            scope='remove_pam_pkcs11_module_check',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='confirm',
                    label='Disable pam_pkcs11 module in PAM configuration? '
                          'If no, the upgrade process will be interrupted.',
                    description='PAM module pam_pkcs11 is no longer available '
                                'in RHEL-8 since it was replaced by SSSD.',
                    reason='Leaving this module in PAM configuration may '
                           'lock out the system.'
                ),
            )
        ),
        Dialog(
            scope='remove_pam_krb5_module_check',
            reason='Confirmation',
            components=(
                BooleanComponent(
                    key='confirm',
                    label='Disable pam_krb5 module in PAM configuration? '
                          'If no, the upgrade process will be interrupted.',
                    description='PAM module pam_krb5 is no longer available '
                                'in RHEL-8 since it was replaced by SSSD.',
                    reason='Leaving this module in PAM configuration may '
                           'lock out the system.'
                ),
            )
        ),
    )

    modules = []

    def process(self):
        model = next(self.consume(RemovedPAMModules))

        for module in model.modules:
            result = self.confirm(module)
            if result:
                self.produce_report(module)
            elif result is False:
                # user specifically chose to disagree with auto disablement
                self.produce_inhibitor(module)

    def confirm(self, module):
        questions = {
            'pam_pkcs11': self.dialogs[0],
            'pam_krb5': self.dialogs[1]
        }

        return self.get_answers(questions[module]).get('confirm')

    def produce_report(self, module):
        create_report([
            reporting.Title('Module {0} will be removed from PAM configuration'.format(module)),
            reporting.Summary(
                'Module {0} was surpassed by SSSD and therefore it was '
                'removed from RHEL-8. Keeping it in PAM configuration may '
                'lock out the system thus it will be automatically removed '
                'from PAM configuration before upgrading to RHEL-8. '
                'Please switch to SSSD to recover the functionality '
                'of {0}.'.format(module)
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS
            ]),
            reporting.Remediation(hint='Configure SSSD to replace {0}'.format(module)),
            reporting.RelatedResource('package', 'sssd')
        ])

    def produce_inhibitor(self, module):
        create_report([
            reporting.Title(
                'Upgrade process was interrupted because {0} is enabled in '
                'PAM configuration and SA user refused to disable it '
                'automatically.'.format(module)),
            reporting.Summary(
                'Module {0} was surpassed by SSSD and therefore it was '
                'removed from RHEL-8. Keeping it in PAM configuration may '
                'lock out the system thus it is necessary to disable it '
                'before the upgrade process can continue.'.format(module)
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.TOOLS,
                    reporting.Groups.INHIBITOR
            ]),
            reporting.Remediation(
                hint='Disable {0} module and switch to SSSD to recover its functionality.'.format(module)),
            reporting.RelatedResource('package', 'sssd')
        ])
