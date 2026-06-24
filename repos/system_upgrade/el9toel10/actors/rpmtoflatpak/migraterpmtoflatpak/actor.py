from leapp.actors import Actor
from leapp.libraries.actor import migraterpmtoflatpak
from leapp.models import RpmToFlatpakFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MigrateRpmToFlatpak(Actor):
    """
    Migrate RPM packages to their Flatpak equivalents on the upgraded system.

    Installs the redhat-flatpak-preinstall-* packages corresponding to each
    RPM package that was detected by ScanRpmToFlatpak. Installing those packages
    triggers `flatpak preinstall` via RPM scriptlets, which pulls in the Flatpak
    application from the configured remote.
    """

    name = 'migrate_rpm_to_flatpak'
    consumes = (RpmToFlatpakFacts,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        migraterpmtoflatpak.process()
