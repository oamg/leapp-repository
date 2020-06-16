from leapp.actors import Actor
from leapp.models import Report, InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag

from leapp.libraries.common.rpms import has_package
from leapp.libraries.actor.library import generate_report


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
        if has_package(InstalledRedHatSignedRPM, 'mariadb-server'):
            generate_report()
