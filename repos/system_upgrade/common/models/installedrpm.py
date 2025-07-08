from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic
from leapp.utils.deprecation import deprecated


class RPM(Model):
    topic = SystemInfoTopic
    name = fields.String()
    epoch = fields.String()
    packager = fields.String()
    version = fields.String()
    release = fields.String()
    arch = fields.String()
    pgpsig = fields.String()
    repository = fields.Nullable(fields.String())
    module = fields.Nullable(fields.String())
    stream = fields.Nullable(fields.String())


class InstalledRPM(Model):
    topic = SystemInfoTopic
    items = fields.List(fields.Model(RPM), default=[])


class DistributionSignedRPM(InstalledRPM):
    """
    Installed packages signed by the vendor of the distribution.
    """
    pass


class ThirdPartyRPM(InstalledRPM):
    """
    Installed packages not signed by the vendor of the distribution.

    This includes:
     - packages signed by other distribution vendors
     - packages signed by other software vendors
     - unsigned packages
    From the POV of in-place upgrades such packages are considered third-party.

    This does not include:
     - packages known not to be signed as they are created by a delivered
       product (which is possibly part of the distribution). E.g. katello RPMS
       created in a Satellite server.
    """
    pass


@deprecated(since='2025-07-09', message='Replaced by ThirdPartyRPM')
class InstalledUnsignedRPM(InstalledRPM):
    pass
