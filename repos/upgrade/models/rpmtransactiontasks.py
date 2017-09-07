from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class RpmTransactionTasks(Model):
    topic = TransactionTopic
    to_install = fields.List(fields.String(), required=True, default=[])
    to_keep = fields.List(fields.String(), required=True, default=[])
    to_remove = fields.List(fields.String(), required=True, default=[])


class FilteredRpmTransactionTasks(RpmTransactionTasks):
    pass
