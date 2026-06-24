from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FlatpakMigrationPackage(Model):
    topic = SystemInfoTopic
    rpm_name = fields.String()
    preinstall_pkg = fields.String()


class RpmToFlatpakFacts(Model):
    """Packages installed as RPMs that will be migrated to Flatpak after upgrade."""
    topic = SystemInfoTopic
    packages = fields.List(fields.Model(FlatpakMigrationPackage), default=[])
