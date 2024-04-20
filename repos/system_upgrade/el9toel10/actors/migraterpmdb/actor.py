from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MigrateRPMDB(Actor):
    """
    Register a workaround to migrate RPM DB during the upgrade.

    The RPM DB has been moved from /var/lib/rpm to /usr/lib/sysimage/rpm
    in RHEL 10. So register "migraterpmdb" script to handle it during various
    parts of the upgrade process. The script moves the dir and create symlink
    /var/lib/rpm -> /usr/lib/sysimage/rpm.

    Note that we realized we should also rebuild the RPM DB, however this is
    handled already in common upgrade repository. So deal here just with paths.
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
