from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FlatpakMigrationPackage(Model):
    """
    Describes a single RPM-to-Flatpak migration.

    Holds the name of the currently installed RPM and the corresponding
    preinstall package that must be present on the target system for
    ``flatpak preinstall`` to pull the Flatpak application.
    """
    topic = SystemInfoTopic

    rpm_name = fields.String()
    """Name of the RPM package installed on the source system."""

    preinstall_pkg = fields.String()
    """Name of the redhat-flatpak-preinstall-* package to install on the target."""


class RpmToFlatpakFacts(Model):
    """
    Aggregated facts about RPM packages that will be migrated to Flatpak.

    Produced by the scanner actor and consumed by the checker (to report
    the planned migration) and the migration actor (to run ``flatpak preinstall``).
    An empty ``packages`` list means no migration is needed.
    """
    topic = SystemInfoTopic

    packages = fields.List(fields.Model(FlatpakMigrationPackage), default=[])
    """List of RPM packages to be migrated to their Flatpak equivalents."""
