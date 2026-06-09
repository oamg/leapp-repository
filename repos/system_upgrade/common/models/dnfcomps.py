from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class DNFGroup(Model):
    """
    Provide information about a single installed DNF comps group.

    This model is not expected to be produced or consumed by any actors as
    a standalone message. It is always part of InstalledDNFComps message.
    """

    topic = SystemFactsTopic

    id = fields.String()
    """
    The DNF comps group identifier (e.g. "core", "base").
    """

    name = fields.String()
    """
    Human-readable display name of the group.
    """

    # NOTE(pstodulk): possible extension if needed in future, but not implemented now:
    # (( to list installed packages, split by various groups ))
    # mandatory_packages = fields.List(fields.String, default=[])
    # default_packages = fields.List(fields.String, default=[])
    # conditional_packages = fields.List(fields.String, default=[])
    # optional_packages = fields.List(fields.String, default=[])


class DNFEnvironment(Model):
    """
    Provide information about a single installed DNF comps environment.

    This model is not expected to be produced or consumed by any actors as
    a standalone message. It is always part of InstalledDNFComps message.
    """

    topic = SystemFactsTopic

    id = fields.String()
    """
    The DNF comps environment identifier (e.g. "minimal-environment").
    """

    name = fields.String()
    """
    Human-readable display name of the environment.
    """

    # NOTE(pstodulk): possible extension if needed in future, but not implemented now:
    # mandatory_groups = fields.List(fields.String(), default=[])
    # optional_groups = fields.List(fields.String(), default=[])


class InstalledDNFComps(Model):
    """
    Provide information about installed DNF comps on the source system.

    Contains lists of installed DNF package environments and groups as
    tracked by the DNF history database.
    """

    topic = SystemFactsTopic

    environments = fields.List(fields.Model(DNFEnvironment), default=[])
    """
    List of installed DNF comps environments.
    """

    groups = fields.List(fields.Model(DNFGroup), default=[])
    """
    List of installed DNF comps groups.
    """
