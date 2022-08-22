from leapp.actors import Actor
from leapp.libraries.actor.postgresqlcheck import report_installed_packages
from leapp.models import InstalledRedHatSignedRPM, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class PostgresqlCheck(Actor):
    """
    Actor checking for presence of PostgreSQL installation.

    Provides user with information related to upgrading systems
    with PostgreSQL installed.
    """
    name = 'postgresql_check'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        report_installed_packages()
