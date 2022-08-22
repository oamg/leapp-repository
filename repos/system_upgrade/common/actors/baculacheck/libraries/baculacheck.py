from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# Summary for bacula-director report
report_director_inst_summary = (
    'Bacula director component will be upgraded. Since the new version is'
    ' incompatible with the current version, it is necessary to proceed'
    ' with additional steps for the complete upgrade of the Bacula backup'
    ' database.'
)

report_director_inst_hint = (
    'Back up your data before proceeding with the upgrade'
    ' and use the command "/usr/libexec/bacula/update_bacula_tables <dbtype>" to upgrade'
    ' the Bacula database after the system upgrade.'
    ' The value of <dbtype> depends on the database backend, possible values are'
    ' sqlite3, mysql, postgresql.'
)


def _report_director_installed():
    """
    Create report on bacula-director package installation detection.

    Should remind user about present Bacula director package
    installation and warn them about necessary additional steps.
    """
    reporting.create_report([
        reporting.Title('bacula (bacula-director) has been detected on your system'),
        reporting.Summary(report_director_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'bacula-director'),
        reporting.Remediation(hint=report_director_inst_hint),
        ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected bacula packages.

    Create the report if the bacula-director rpm (RH signed) is installed.
    """
    has_director = has_package(InstalledRedHatSignedRPM, 'bacula-director', context=_context)

    if has_director:
        # bacula-director
        _report_director_installed()
