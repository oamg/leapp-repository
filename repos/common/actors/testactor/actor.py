from leapp.actors import Actor
from leapp.models import Test
from leapp.tags import TestTag

class TestActor(Actor):
    name = 'test_actor'
    description = 'For the actor test_actor has been no description provided.'
    consumes = ()
    produces = (Test,)
    tags = (TestTag,)

    def process(self):
        self.log.info("Test actor started")
        self.produce(Test(value='A string value'))
        self.log.info("Test actor finished")
