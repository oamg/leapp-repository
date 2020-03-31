from leapp.models import Model, fields
from leapp.topics import TransactionTopic


class TargetRepositoryBase(Model):
    topic = TransactionTopic
    repoid = fields.String()


class UsedTargetRepository(TargetRepositoryBase):
    pass


class RHELTargetRepository(TargetRepositoryBase):
    pass


class CustomTargetRepository(TargetRepositoryBase):
    name = fields.Nullable(fields.String())
    baseurl = fields.Nullable(fields.String())
    enabled = fields.Boolean(default=True)


class TargetRepositories(Model):
    topic = TransactionTopic
    rhel_repos = fields.List(fields.Model(RHELTargetRepository))
    custom_repos = fields.List(fields.Model(CustomTargetRepository), default=[])


class UsedTargetRepositories(Model):
    topic = TransactionTopic
    repos = fields.List(fields.Model(UsedTargetRepository))


class CustomTargetRepositoryFile(Model):
    topic = TransactionTopic
    file = fields.String()
