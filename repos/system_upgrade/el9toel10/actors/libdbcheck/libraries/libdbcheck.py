from leapp import reporting
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM


def _report_libdb_installed():
    """
    Create report on libdb package installation detection.

    Should remind user about present libdb package
    installation, warn them about the lack of libdb support in RHEL 10, and
    redirect them to online documentation for the migration process.
    """
    summary = (
        'Libdb was marked as deprecated in {source_distro} 9 and in'
        ' {target_distro} 10 is not included anymore.'
        ' There are a couple of alternatives in {target_distro} 10; the applications that'
        ' depend on libdb will not work. Such applications must implement another'
        ' type of backend storage. And migrate existing data to the new database format.'
    ).format_map(DISTRO_REPORT_NAMES)

    hint_text = (
        'Back up your data before proceeding with the data upgrade/migration.'
        ' For the conversion, the tool db_converter from the libdb-utils'
        ' rpm could be used. This database format conversion must be performed'
        ' before the system upgrade. The db_converter is not available in'
        ' {target_distro} 10 systems. For more information, see the provided article.'
    ).format_map(DISTRO_REPORT_NAMES)

    reporting.create_report([
        reporting.Title('Berkeley DB (libdb) has been detected on your system'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 10 without libdb',
                               url='https://access.redhat.com/articles/7099256'),
        reporting.RelatedResource('package', 'libdb'),
        reporting.Remediation(hint=hint_text),
    ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected libdb packages.

    Create the report if the libdb rpm (RH signed) is installed.
    """
    has_libdb = has_package(DistributionSignedRPM, 'libdb', context=_context)

    if has_libdb:
        _report_libdb_installed()
