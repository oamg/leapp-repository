from leapp.actors import Actor
from leapp.libraries.actor.mysqlcheck import MySQLCheckLib
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
        lib = MySQLCheckLib()
        lib.report_installed_packages()
