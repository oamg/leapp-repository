from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class TargetUserSpaceInfo(Model):
    topic = TransactionTopic
    path = fields.String()
    scratch = fields.String()
    mounts = fields.String()
