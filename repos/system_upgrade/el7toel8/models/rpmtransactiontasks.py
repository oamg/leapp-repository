from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class RpmTransactionTasks(Model):
    topic = TransactionTopic
    to_install = fields.List(fields.String(), default=[])
    to_keep = fields.List(fields.String(), default=[])
    to_remove = fields.List(fields.String(), default=[])


class FilteredRpmTransactionTasks(RpmTransactionTasks):
    pass
