from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class VdoConversionDevice(Model):
    topic = SystemInfoTopic
    name = fields.String()


class VdoConversionPreDevice(VdoConversionDevice):
    pass


class VdoConversionFailiableDevice(VdoConversionDevice):
    # `check_failed` and `failure` are only set if the checking process fails.
    check_failed = fields.Boolean(default=False)
    failure = fields.Nullable(fields.String())


class VdoConversionPostDevice(VdoConversionFailiableDevice):
    complete = fields.Boolean()


class VdoConversionUndeterminedDevice(VdoConversionFailiableDevice):
    # There are only devices which are undetermined as to VDO conversion if
    # lvm is installed on the system and either vdo is not or
    # `vdoprepareforlvm` fails.
    #
    # If the vdo package is not installed on the system `check_failed` is
    # false (the device wasn't actually checked); this indicates the absence of
    # the vdo package on the system.
    pass


class VdoConversionInfo(Model):
    # If lvm is not installed on the system there can be no VDO instances.
    # In that case VdoConversionInfo is generated with empty lists of devices.
    topic = SystemInfoTopic

    pre_conversion = fields.List(fields.Model(VdoConversionPreDevice), default=[])
    post_conversion = fields.List(fields.Model(VdoConversionPostDevice), default=[])
    undetermined_conversion = fields.List(fields.Model(VdoConversionUndeterminedDevice), default=[])
