from leapp.actors import Actor
from leapp.libraries.actor import scanmysql
from leapp.models import DistributionSignedRPM, MySQLConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanMySQL(Actor):
    """
    Actor checking for presence of MySQL installation.

    If MySQL server is found it will check whether current configuration is not
    deprecated and produce all options and arguments that are in use and are
    deprecated. These are removed in newer version of MySQL that is present in
    RHEL10.

    List of options:
        https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html
    List of arguments: (usable only as an argument for mysqld - systemd service)
        https://dev.mysql.com/doc/refman/8.0/en/server-options.html
    Complete documentation of changes in newer MySQL - including removed
    options:
        https://dev.mysql.com/doc/refman/8.4/en/mysql-nutshell.html
    """
    name = 'scan_mysql'
    consumes = (DistributionSignedRPM,)
    produces = (MySQLConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self) -> None:
        self.produce(scanmysql.check_status())
