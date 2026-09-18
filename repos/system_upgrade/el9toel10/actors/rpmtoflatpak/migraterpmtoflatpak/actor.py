from leapp.actors import Actor
from leapp.libraries.actor import migraterpmtoflatpak
from leapp.models import RpmToFlatpakFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateRpmToFlatpak(Actor):
    """
    Migrate RPM packages to their Flatpak equivalents on the upgraded system.

    Runs ``flatpak preinstall`` to pull in the Flatpak applications from the
    required remotes as defined in the preinstall configuration. The
    redhat-flatpak-preinstall-* packages and flatpak itself are already
    installed at this point via RpmTransactionTasks produced by the scanner.
    """

    name = 'migrate_rpm_to_flatpak'
    consumes = (RpmToFlatpakFacts,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        migraterpmtoflatpak.process()
