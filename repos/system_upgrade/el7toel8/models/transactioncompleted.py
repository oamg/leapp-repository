from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class TransactionCompleted(Model):
    topic = TransactionTopic
