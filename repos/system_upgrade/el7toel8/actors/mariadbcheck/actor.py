from leapp.actors import Actor
from leapp.reporting import Report
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

from leapp.libraries.actor.library import get_mariadb_packages, generate_report


class MariaDbCheck(Actor):
    """
    Check for RedHat Signed MariaDB installation and warn user about possible
    manual intervention requirements.
    """

    name = 'mariadb_check'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        packages = get_mariadb_packages()

        if packages:
            generate_report(packages)
        

