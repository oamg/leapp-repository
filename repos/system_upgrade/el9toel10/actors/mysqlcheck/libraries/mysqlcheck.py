from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

import subprocess


class MySQLCheckLib:
    REMOVED_ARGS = [
        '--avoid-temporal-upgrade',
        '--show-old-temporals',
        '--old',
        '--new',
        '--default-authentication-plugin',
        '--no-dd-upgrade',
        '--language',
        '--ssl',
        '--admin-ssl',
        '--character-set-client-handshake',
        '--old-style-user-limits',
    ]

    # Summary for mysql-server report
    report_server_inst_summary = (
        'MySQL server component will be upgraded.\n'
        'Since RHEL-10 includes MySQL server 8.4 by default, it might be necessary'
        ' to proceed with additional steps.'
        '\n'
    )

    report_server_inst_hint = (
        'Back up your data before proceeding with the upgrade'
        ' and follow steps in the documentation section "Migrating to a RHEL 10 version of MySQL"'
        ' after the upgrade.'
    )

    # Link URL for mysql-server report
    report_server_inst_link_url = 'https://access.redhat.com/articles/7099234'

    # Default title
    report_title = 'MySQL (mysql-server) has been detected on your system'

    # Default severity
    report_severity = reporting.Severity.MEDIUM

    found_arguments = set()
    found_options = set()

    def _generate_report(self):
        """
        Create report on mysql-server package installation detection.

        Should remind user about present MySQL server package
        installation, warn them about necessary additional steps, and
        redirect them to online documentation for the upgrade process.
        """

        if self.found_arguments or self.found_options:
            self.report_severity = reporting.Severity.HIGH
            self.report_title = 'MySQL (mysql-server) seems to be using deprecated config options'
            self.report_server_inst_summary += (
                '\nWarning:\n'
                'It seems that some config options currently used for MySQL server'
                ' will be removed in updated MySQL server.\n'
                'If you proceed with the update now, without addressing this issue,'
                ' the MySQL server will fail to start until the config is fixed.\n'
                'Detected deprecated options:\n'
            )
            for arg in self.found_options:
                self.report_server_inst_summary += f"{arg} in MySQL config file\n"
            for arg in self.found_arguments:
                self.report_server_inst_summary += f"{arg} in SystemD service override\n"

        reporting.create_report([
            reporting.Title(self.report_title),
            reporting.Summary(self.report_server_inst_summary),
            reporting.Severity(self.report_severity),
            reporting.Groups([reporting.Groups.SERVICES]),
            reporting.ExternalLink(title='Migrating to a RHEL 10 version of MySQL',
                                   url=self.report_server_inst_link_url),
            reporting.RelatedResource('package', 'mysql-server'),
            reporting.Remediation(hint=self.report_server_inst_hint),
            ])

    def _check_incompatible_config(self):
        # mysqld --validate-config --log-error-verbosity=2
        # 2024-12-18T11:40:04.725073Z 0 [Warning] [MY-011069] [Server]
        # The syntax '--old' is deprecated and will be removed in a future release.
        out = subprocess.run(['mysqld', '--validate-config', '--log-error-verbosity=2'],
                             capture_output=True,
                             check=False)

        stderr = out.stderr.decode("utf-8")
        if 'deprecated' in stderr:
            self.found_options = {arg for arg
                                  in self.REMOVED_ARGS
                                  if arg in stderr}

    def _check_incompatible_launch_param(self):
        # Check /etc/systemd/system/mysqld.service.d/override.conf
        try:
            with open('/etc/systemd/system/mysqld.service.d/override.conf') as f:
                file_content = f.read()
                self.found_arguments = {arg for arg
                                        in self.REMOVED_ARGS
                                        if arg in file_content}
        except OSError:
            # File probably doesn't exist, ignore it and pass
            pass

    def report_installed_packages(self, _context=api):
        """
        Create reports according to detected MySQL packages.

        Create the report if the mysql-server rpm (RH signed) is installed.
        """

        self._check_incompatible_config()
        self._check_incompatible_launch_param()

        if has_package(DistributionSignedRPM, 'mysql-server', context=_context):
            self._generate_report()
