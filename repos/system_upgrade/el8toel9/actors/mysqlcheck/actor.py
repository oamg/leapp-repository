from leapp.actors import Actor
from leapp.libraries.actor.mysqlcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MySQLCheck(Actor):
    """
    Actor checking for presence of MySQL installation.

    Provides user with information related to upgrading systems
    with MySQL installed.
    """
    name = 'mysql_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
