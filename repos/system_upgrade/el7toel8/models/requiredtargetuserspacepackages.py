from leapp.models import Model, fields
from leapp.topics import TargetUserspaceTopic


class RequiredTargetUserspacePackages(Model):
    topic = TargetUserspaceTopic
    packages = fields.List(fields.String(), default=[])
