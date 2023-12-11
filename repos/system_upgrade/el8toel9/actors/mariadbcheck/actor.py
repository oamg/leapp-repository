from leapp.actors import Actor
from leapp.libraries.actor.mariadbcheck import report_installed_packages
from leapp.models import DistributionSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MariadbCheck(Actor):
    """
    Actor checking for presence of MariaDB installation.

    Provides user with information related to upgrading systems
    with MariaDB installed.
    """
    name = 'mariadb_check'
    consumes = (DistributionSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
