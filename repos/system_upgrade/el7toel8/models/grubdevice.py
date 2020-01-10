from leapp.models import Model, fields
from leapp.topics import SystemFactsTopic


class GrubDevice(Model):
    topic = SystemFactsTopic

    grub_device = fields.String()


class UpdateGrub(Model):
    topic = SystemFactsTopic

    grub_device = fields.String()
