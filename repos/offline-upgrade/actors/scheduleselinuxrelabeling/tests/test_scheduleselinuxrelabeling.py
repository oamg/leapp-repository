import os

from leapp.snactor.fixture import current_actor_context
from leapp.models import SelinuxRelabelDecision


def test_schedule_no_relabel(current_actor_context):
    current_actor_context.feed(SelinuxRelabelDecision(set_relabel=False))
    current_actor_context.run()
    assert not os.path.isfile('/.autorelabel')


def test_schedule_relabel(current_actor_context):
    current_actor_context.feed(SelinuxRelabelDecision(set_relabel=True))
    current_actor_context.run()
    assert os.path.isfile('/.autorelabel')

    # lets cleanup so we possibly not affect further testing
    os.unlink('/.autorelabel')
