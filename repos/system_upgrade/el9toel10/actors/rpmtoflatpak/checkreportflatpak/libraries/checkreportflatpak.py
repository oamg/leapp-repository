from leapp import reporting
from leapp.libraries.common.rhsm import skip_rhsm
from leapp.libraries.stdlib import api
from leapp.models import RpmToFlatpakFacts, RpmTransactionTasks

_FLATPAK_PKG = 'flatpak'
# flatpak preinstall is run through dbus-run-session (dbus-tools), which starts a
# D-Bus daemon (dbus-daemon). Neither package is installed on systems without a
# graphical environment, so make sure both are present on the target.
_DBUS_PKGS = ['dbus-tools', 'dbus-daemon']
_FLATPAK_DOCS_URL = 'https://red.ht/rhel10-installing-flatpak-applications'


def _report_migration_not_enabled(rpm_names):
    pkg_list = ', '.join(rpm_names)

    summary = (
        'The following packages are installed as RPMs but are no longer shipped as RPMs '
        'starting with RHEL 10.2: {packages}. These packages are available as Flatpaks '
        'on RHEL 10.\n\n'
        'Automatic RPM-to-Flatpak migration is currently only supported on systems '
        'using Red Hat Subscription Manager (RHSM).'
    ).format(packages=pkg_list)

    reporting.create_report([
        reporting.Title(
            'RPM-to-Flatpak migration is not enabled on this system'
        ),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.DESKTOP]),
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
        'starting with RHEL 10.2. They will be migrated to their Flatpak equivalents '
        'during the first boot of the upgraded system: {packages}.\n\n'
        'The corresponding redhat-flatpak-preinstall-* packages and the flatpak package '
        'itself are installed on the target system as part of the upgrade transaction. '
        'Once the system boots into the upgraded system, `flatpak preinstall` is run to '
        'install the applications. This requires a working network connection.'
    ).format(packages=pkg_list)

    reporting.create_report([
        reporting.Title(
            'Some RPM packages will be migrated to Flatpak'
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
        _report_migration_not_enabled(rpm_names)
        return

    to_install = [_FLATPAK_PKG] + _DBUS_PKGS + [p.preinstall_pkg for p in facts.packages]
    api.produce(RpmTransactionTasks(to_install=to_install))

    _report_migration(rpm_names)
