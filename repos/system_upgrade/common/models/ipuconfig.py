from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class EnvVar(Model):
    topic = SystemInfoTopic

    name = fields.String()
    """Name of the environment variable."""

    value = fields.String()
    """Value of the environment variable."""


class OSRelease(Model):
    topic = SystemInfoTopic

    release_id = fields.String()
    name = fields.String()
    pretty_name = fields.String()
    version = fields.String()
    version_id = fields.String()
    variant = fields.Nullable(fields.String())  # isn't specified on some systems
    variant_id = fields.Nullable(fields.String())  # same as above


class Version(Model):
    topic = SystemInfoTopic

    source = fields.String()
    """Version of the source (current) system. E.g.: '7.8'."""

    target = fields.String()
    """Version of the target system. E.g. '8.2.'."""


class IPUConfig(Model):
    """
    IPU workflow configuration model
    """
    topic = SystemInfoTopic

    leapp_env_vars = fields.List(fields.Model(EnvVar), default=[])
    """Environment variables related to the leapp."""

    os_release = fields.Model(OSRelease)
    """Data about the OS get from /etc/os-release."""

    version = fields.Model(Version)
    """Version of the current (source) system and expected target system."""

    architecture = fields.String()
    """Architecture of the system. E.g.: 'x86_64'."""

    kernel = fields.String()
    """Originally booted kernel when on the source system."""

    flavour = fields.StringEnum(('default', 'saphana'), default='default')
    """Flavour of the upgrade - Used to influence changes in supported source/target release"""
