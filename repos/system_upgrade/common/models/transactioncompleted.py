from leapp.models import Model
from leapp.topics import TransactionTopic


class TransactionCompleted(Model):
    topic = TransactionTopic
