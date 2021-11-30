from leapp.models import fields, Model, RPM
from leapp.topics import TransactionTopic


class LeftoverPackages(Model):
    topic = TransactionTopic
    items = fields.List(fields.Model(RPM), default=[])


class RemovedPackages(LeftoverPackages):
    pass
