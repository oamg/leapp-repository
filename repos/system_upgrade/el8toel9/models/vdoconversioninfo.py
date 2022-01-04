from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class VdoConversion(Model):
    topic = SystemInfoTopic
    name = fields.String()


class VdoPostConversion(VdoConversion):
    complete = fields.Boolean()


class VdoPreConversion(VdoConversion):
    pass


class VdoConversionInfo(Model):
    topic = SystemInfoTopic

    pre_conversion_vdos = fields.List(fields.Model(VdoPreConversion), default = [])
    post_conversion_vdos = fields.List(fields.Model(VdoPostConversion), default = [])
