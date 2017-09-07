from leapp.actors import Actor
from leapp.models import Test
from leapp.tags import TestTag

class TestActorInternal(Actor):
    name = 'test_actor_internal'
    description = 'Dummy test for internall repo.'
    consumes = ()
    produces = (Test,)
    tags = (TestTag,)

    def process(self):
        self.log.info("Test actor internal started")
        self.produce(Test(value='A string value'))
        self.log.info("Test actor internal finished")
