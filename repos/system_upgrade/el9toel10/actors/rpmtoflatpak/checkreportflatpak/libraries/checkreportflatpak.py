from leapp import reporting
from leapp.libraries.common.rhsm import skip_rhsm
from leapp.libraries.stdlib import api
from leapp.models import RpmToFlatpakFacts, RpmTransactionTasks

_FLATPAK_PKG = 'flatpak'
_FLATPAK_DOCS_URL = (
    'https://docs.redhat.com/documentation/red_hat_enterprise_linux/10/html'
    '/administering_rhel_by_using_the_gnome_desktop_environment/installing-applications-by-using-flatpak'
)


def _report_inhibitor(rpm_names):
    pkg_list = ', '.join(rpm_names)

    summary = (
        'The following packages are installed as RPMs but are no longer shipped as RPMs '
        'on the target system: {packages}. These packages are available as Flatpaks '
        'on RHEL 10.\n\n'
        'Automatic RPM-to-Flatpak migration is currently only supported on systems '
        'using Red Hat Subscription Manager (RHSM). This system is not using RHSM '
        '(LEAPP_NO_RHSM=1 is set).\n\n'
        'After the upgrade, install the applications manually as Flatpaks.'
    ).format(packages=pkg_list)

    reporting.create_report([
        reporting.Title(
            'RPM-to-Flatpak migration is not supported without RHSM'
        ),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR, reporting.Groups.DESKTOP]),
        reporting.Remediation(
            hint='After the upgrade, install the applications as Flatpaks manually.'
        ),
        reporting.ExternalLink(
            url=_FLATPAK_DOCS_URL,
            title='Installing applications by using Flatpak'
        ),
    ])


def _report_migration(rpm_names):
    pkg_list = ', '.join(rpm_names)

    summary = (
        'The following packages are installed as RPMs but are no longer shipped as RPMs '
        'on the target system. They will be migrated to their Flatpak equivalents '
        'during the upgrade: {packages}.\n\n'
        'The migration is performed by installing the corresponding '
        'redhat-flatpak-preinstall-* packages and the flatpak package itself on the '
        'target system as part of the upgrade transaction, then running '
        '`flatpak preinstall`.'
    ).format(packages=pkg_list)

    reporting.create_report([
        reporting.Title(
            'RPM packages will be migrated to Flatpak'
        ),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.DESKTOP]),
        reporting.ExternalLink(
            url=_FLATPAK_DOCS_URL,
            title='Installing applications by using Flatpak'
        ),
    ])


def process():
    facts = next(api.consume(RpmToFlatpakFacts), None)
    if not facts or not facts.packages:
        return

    rpm_names = sorted(p.rpm_name for p in facts.packages)

    if skip_rhsm():
        _report_inhibitor(rpm_names)
        return

    to_install = [_FLATPAK_PKG] + [p.preinstall_pkg for p in facts.packages]
    api.produce(RpmTransactionTasks(to_install=to_install))

    _report_migration(rpm_names)
