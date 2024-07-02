from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MigrateRPMDB(Actor):
    """
    Registers a workaround which will migrate RPM DB during the upgrade.
    """

    name = 'migrate_rpm_db'
    consumes = ()
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(
            DNFWorkaround(
                display_name="Migrate RPM DB",
                script_path=self.get_tool_path("migraterpmdb"),
            )
        )
