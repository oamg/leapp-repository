from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic
from leapp.utils.deprecation import deprecated


@deprecated(
    since='2026-06-04',
    message='This model has been deprecated! Use KernelInfo model for information about source distribution kernel.'
)
class CurrentKernel(Model):
    topic = SystemInfoTopic
    version = fields.String()
    release = fields.String()
    arch = fields.String()
