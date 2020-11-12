from leapp import reporting
from leapp.actors import Actor
from leapp.models import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class UnsupportedUpgradeCheck(Actor):
    """
    Checks enviroment variables and produces a warning report if the upgrade is unsupported.

    Upgrade is unsupported if any LEAPP_DEVEL_* variable is used or an experimental actor is enabled.
    This can be overridden by setting the variable LEAPP_UNSUPPORTED (at user's own risk).
    """

    name = 'unsupported_upgrade_check'
    consumes = ()
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        leapp_vars = self.configuration.leapp_env_vars
        devel_vars = [v for v in leapp_vars if v.name.startswith('LEAPP_DEVEL_')]
        experimental = bool([v for v in leapp_vars if v.name == 'LEAPP_EXPERIMENTAL' and v.value == '1'])
        override = bool([v for v in leapp_vars if v.name == 'LEAPP_UNSUPPORTED' and v.value == '1'])

        if override:
            reporting.create_report([
                reporting.Title('Upgrade is unsupported'),
                reporting.Summary(
                    'Environment variable LEAPP_UNSUPPORTED has been detected. A successful and safe '
                    'upgrade process cannot be guaranteed. From now on you are continuing at your own '
                    'risk.\n'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.UPGRADE_PROCESS, reporting.Groups.SANITY]),
            ])

        else:
            if devel_vars:
                reporting.create_report([
                    reporting.Title('Upgrade inhibited due to usage of development variables'),
                    reporting.Summary(
                        'One or more environment variables in the form of LEAPP_DEVEL_* have been detected.\n'
                        'These variables are for development purposes only and can interfere with the upgrade '
                        'process in unexpected ways. As such, a successful and safe upgrade process cannot be '
                        'guaranteed and the upgrade is unsupported.\n'
                        'You can bypass this error by setting the LEAPP_UNSUPPORTED variable but by doing so, '
                        'you continue at your own risk.\n'
                        'Found development variables:\n- {}\n'.format('\n- '.join([v.name for v in devel_vars]))
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.UPGRADE_PROCESS,
                                      reporting.Groups.SANITY,
                                      reporting.Groups.INHIBITOR]),
                    reporting.Remediation(hint=('Invoke leapp without any LEAPP_DEVEL_* environment variables '
                                                'or set LEAPP_UNSUPPORTED=1.'))
                ])

            if experimental:
                reporting.create_report([
                    reporting.Title('Upgrade inhibited due to enabled experimental actors'),
                    reporting.Summary(
                        'One or more enabled experimental actors have been detected.\n'
                        'These actors are unstable or in development and can interfere with the upgrade '
                        'process in unexpected ways. As such, a successful and safe upgrade process cannot be '
                        'guaranteed and the upgrade is unsupported.\n'
                        'You can bypass this error by setting the LEAPP_UNSUPPORTED variable but by doing so, '
                        'you continue at your own risk.\n'
                    ),
                    reporting.Severity(reporting.Severity.HIGH),
                    reporting.Groups([reporting.Groups.UPGRADE_PROCESS,
                                      reporting.Groups.SANITY,
                                      reporting.Groups.INHIBITOR]),
                    reporting.Remediation(hint=('Invoke leapp without any --whitelist-experimental options '
                                                'or set LEAPP_UNSUPPORTED=1.'))
                ])
