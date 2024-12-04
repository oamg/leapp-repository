from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

# Summary for libdb report
report_libdb_inst_summary = (
    'Libdb was marked as deprecated in RHEL-9 and in RHEL-10 is not included anymore.'
    ' There are a couple of alternatives in RHEL-10; the applications that'
    ' depend on libdb will not work. Such applications must implement another'
    ' type of backend storage. And migrate existing data to the new database format.'
)

report_libdb_inst_hint = (
    'Back up your data before proceeding with the data upgrade/migration.'
    ' For the conversion, the tool db_converter from the libdb-utils'
    ' rpm could be used. This database format conversion must be performed'
    ' before the system upgrade. The db_converter is not available in RHEL 10'
    ' systems. For more information, see the provided article.'
)

# Link URL for libdb report
report_libdb_inst_link_url = 'https://access.redhat.com/articles/7099256'


def _report_libdb_installed():
    """
    Create report on libdb package installation detection.

    Should remind user about present libdb package
    installation, warn them about the lack of libdb support in RHEL 10, and
    redirect them to online documentation for the migration process.
    """
    reporting.create_report([
        reporting.Title('Berkeley DB (libdb) has been detected on your system'),
        reporting.Summary(report_libdb_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 10 without libdb',
                               url=report_libdb_inst_link_url),
        reporting.RelatedResource('package', 'libdb'),
        reporting.Remediation(hint=report_libdb_inst_hint),
        ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected libdb packages.

    Create the report if the libdb rpm (RH signed) is installed.
    """
    has_libdb = has_package(DistributionSignedRPM, 'libdb', context=_context)

    if has_libdb:
        _report_libdb_installed()
