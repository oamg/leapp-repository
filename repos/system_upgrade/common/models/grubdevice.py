from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic
from leapp.utils.deprecation import deprecated


@deprecated(
    since='2020-09-01',
    message=(
        'The model is deprecated as the current implementation was not reliable. '
        'We moved the GRUB device detection into grub library. '
        'Please use get_grub_device() function instead.'
    )
)
class GrubDevice(Model):
    topic = SystemFactsTopic

    grub_device = fields.String()


@deprecated(
    since='2020-09-01',
    message=(
        'The model is deprecated as the current implementation was not reliable. '
        'We moved the GRUB device detection into grub library. '
        'Please use get_grub_device() function instead.'
    )
)
class UpdateGrub(Model):
    topic = SystemFactsTopic

    grub_device = fields.String()
