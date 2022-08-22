from leapp import reporting
from leapp.actors import Actor
from leapp.models import SSSDConfig8to9
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

COMMON_REPORT_TAGS = [reporting.Groups.AUTHENTICATION, reporting.Groups.SECURITY]

related = [
    reporting.RelatedResource('package', 'sssd'),
    reporting.RelatedResource('file', '/etc/sssd/sssd.conf')
]


class SSSDCheck8to9(Actor):
    """
    Check SSSD configuration for changes in RHEL9 and report them in model.

    Implicit files domain is disabled by default. This may affect local
    smartcard authentication if there is not explicit files domain created.

    If there is no files domain and smartcard authentication is enabled,
    we will notify the administrator.
    """

    name = 'sssd_check_8to9'
    consumes = (SSSDConfig8to9,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        model = next(self.consume(SSSDConfig8to9), None)
        if not model:
            return

        # enable_files_domain is set explicitly, change of default has no effect
        if model.enable_files_domain_set:
            return

        # there is explicit files domain, implicit files domain has no effect
        if model.explicit_files_domain:
            return

        # smartcard authentication is disabled, implicit files domain has no effect
        if not model.pam_cert_auth:
            return

        create_report([
            reporting.Title('SSSD implicit files domain is now disabled by default.'),
            reporting.Summary('Default value of [sssd]/enable_files_domain has '
                              'changed from true to false.'),
            reporting.Groups(COMMON_REPORT_TAGS),
            reporting.Remediation(
                hint='If you use smartcard authentication for local users, '
                     'set this option to true explicitly and call '
                     '"authselect enable-feature with-files-domain".'
            ),
            reporting.Severity(reporting.Severity.MEDIUM)
        ] + related)
