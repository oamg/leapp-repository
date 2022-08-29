from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, NISConfig

report_summary = (
    'The NIS components (ypserv, ypbind, and yp-tools) are no longer available in RHEL-9.'
    ' The technology behind those packages is based an outdated design patterns, which are'
    ' no longer considered as secure. There is no direct alternative with fully compatible'
    ' features.'
)

report_hint = (
    'The alternatives are LDAP and for some use cases Kerberos or migrating to IPA.'
)

report_link_url = 'https://access.redhat.com/solutions/5991271'


def report_nis():
    """
    Create the report if any of NIS packages (RH signed)
    is installed and configured.

    Should notify user about present NIS component package
    installation, warn them about discontinuation, and
    redirect them to online documentation for possible
    alternatives.
    """

    installed_packages = []
    configured_rpms = []

    # Get necessary models created by another actors
    nis_confs = api.consume(NISConfig)
    nis_conf = next(nis_confs, None)
    if not nis_conf:
        raise StopActorExecutionError(
            'Could not obtain NIS RPM information',
            details={'details': 'Actor did not receive NISConfig message.'}
        )

    if next(nis_confs, None):
        api.current_logger().warning('Unexpectedly received more than one NISConfig message.')

    configured_rpms = nis_conf.nis_not_default_conf

    installed_packages = [package for package in (
        'ypserv', 'ypbind') if has_package(InstalledRedHatSignedRPM, package)]

    # Final list of NIS packages (configured and installed)
    rpms_configured_installed = [x for x in installed_packages if x in configured_rpms]

    if not rpms_configured_installed:
        return

    # Create report
    report_content = [
        reporting.Title('NIS component has been detected on your system'),
        reporting.Summary(report_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='RHEL 9 (NIS) discontinuation',
                               url=report_link_url),
        reporting.Remediation(hint=report_hint),
    ]

    related_resources = [reporting.RelatedResource('package', pkg) for pkg in rpms_configured_installed]
    report_content += related_resources

    reporting.create_report(report_content)
