from leapp.models import Model, fields
from leapp.topics import TestTopic

class Test(Model):
    topic = TestTopic
    value = fields.String()
