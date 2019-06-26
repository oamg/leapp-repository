from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class EnvVar(Model):
    topic = SystemInfoTopic

    name = fields.String()
    value = fields.String()


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
    target = fields.String()


class IPUConfig(Model):
    """
    IPU workflow configuration model
    """
    topic = SystemInfoTopic

    leapp_env_vars = fields.List(fields.Model(EnvVar), default=[])
    os_release = fields.Model(OSRelease)
    version = fields.Model(Version)
    architecture = fields.String()
