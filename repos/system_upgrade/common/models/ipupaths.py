from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic
from leapp.utils.deprecation import deprecated


class IPUPath(Model):
    """
    Represent upgrade paths from a source system version.

    This model is not supposed to be produced nor consumed directly by any actor.
    See `IPUPaths` instead.
    """
    topic = SystemInfoTopic

    source_version = fields.String()
    """Version of a particular source system."""

    target_versions = fields.List(fields.String())
    """List of defined target system versions for the `source_version` system."""


@deprecated(
    since="2025-02-01",
    message="This model is temporary and not assumed to be used in any actors."
)
class IPUPaths(Model):
    """
    Defined Upgrade paths from the source system major version and used upgrade flavour.

    In example for the RHEL 8.10 system with the 'default' upgrade flavour it will
    contain information about all defined upgrade paths from any RHEL 8 system
    for the 'default' flavour (other flavour can be e.g. 'saphana' for systems
    with SAP HANA installed.

    Note this model is marked as deprecated now as it is considered as a temporary
    solution. It can be removed in any future release!
    """
    topic = SystemInfoTopic

    data = fields.List(fields.Model(IPUPath))
    """
    List of defined (filtered) upgrade paths.
    """
