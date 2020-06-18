import logging

import pytest

from leapp.actors import Actor
from leapp.libraries.common.utils import skip_actor_execution_if


@pytest.mark.parametrize(
    ('conditions', 'exp_return', 'exp_msg_in_log'),
    [
        ((True,), None, 'processing skipped'),
        ((True, True), None, 'processing skipped'),
        ((True, False), None, 'processing skipped'),
        ((False,), 'processed', None),
        ((False, False), 'processed', None),
    ],
)
def test_skip_actor_if(conditions, exp_return, exp_msg_in_log, caplog):
    class SomeActor(Actor):
        name = 'some_actor'
        consumes = ()
        produces = ()
        tags = ()

        def process(self):
            return 'processed'

    DecoratedActor = skip_actor_execution_if(*conditions)(SomeActor)
    decorated_actor = DecoratedActor()
    with caplog.at_level(logging.DEBUG):
        assert decorated_actor.process() == exp_return
    if exp_msg_in_log:
        assert exp_msg_in_log in caplog.text


def test_skip_actor_if_not_actor_subclass(caplog):
    with caplog.at_level(logging.DEBUG):

        @skip_actor_execution_if(False)
        class A(object):
            pass
        A()

    assert 'decorator can be used only for Actor' in caplog.text
