from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# Summary for postgresql-server report
report_server_inst_summary = (
    'PostgreSQL server component will be upgraded. Since RHEL-8 includes'
    ' PostgreSQL server 10 by default, which is incompatible with 9.2'
    ' included in RHEL-7, it is necessary to proceed with additional steps'
    ' for the complete upgrade of the PostgreSQL data.'
)

report_server_inst_hint = (
    'Back up your data before proceeding with the upgrade'
    ' and follow steps in the documentation section "Migrating to a RHEL 8 version of PostgreSQL"'
    ' after the upgrade.'
)

# Link URL for postgresql-server report
report_server_inst_link_url = 'https://red.ht/rhel-8-migrate-postgresql-server'

# List of dropped extensions from postgresql-contrib package
report_contrib_inst_dropext = ['dummy_seclabel', 'test_parser', 'tsearch2']

# Summary for postgresql-contrib report
report_contrib_inst_summary = (
    'Please note that some extensions have been dropped from the'
    ' postgresql-contrib package and might not be available after'
    ' the upgrade:{}'
    .format(''.join(['\n    - {}'.format(i) for i in report_contrib_inst_dropext]))
)


def _report_server_installed():
    """
    Create report on postgresql-server package installation detection.

    Should remind user about present PostgreSQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """
    reporting.create_report([
        reporting.Title('PostgreSQL (postgresql-server) has been detected on your system'),
        reporting.Summary(report_server_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating to a RHEL 8 version of PostgreSQL',
                               url=report_server_inst_link_url),
        reporting.RelatedResource('package', 'postgresql-server'),
        reporting.Remediation(hint=report_server_inst_hint),
        ])


def _report_contrib_installed():
    """
    Create report on postgresql-contrib package installation detection.

    Should remind user about present PostgreSQL contrib package
    installation and provide them with a list of extensions no longer
    shipped with this package.
    """
    reporting.create_report([
        reporting.Title('PostgreSQL (postgresql-contrib) has been detected on your system'),
        reporting.Summary(report_contrib_inst_summary),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'postgresql-contrib')
        ])


def report_installed_packages(_context=api):
    """
    Create reports according to detected PostgreSQL packages.

    Create the report if the postgresql-server rpm (RH signed) is installed.
    Additionally, create another report if the postgresql-contrib rpm
    is installed.
    """
    has_server = has_package(InstalledRedHatSignedRPM, 'postgresql-server', context=_context)
    has_contrib = has_package(InstalledRedHatSignedRPM, 'postgresql-contrib', context=_context)

    if has_server:
        # postgresql-server
        _report_server_installed()
        if has_contrib:
            # postgresql-contrib
            _report_contrib_installed()
