import os

import pytest

from leapp.models import SelinuxRelabelDecision
from leapp.snactor.fixture import current_actor_context

# TODO These tests modifies the system


@pytest.mark.skipif(
    os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
    reason='Test disabled by default because it would modify the system',
)
def test_schedule_no_relabel(current_actor_context):
    current_actor_context.feed(SelinuxRelabelDecision(set_relabel=False))
    current_actor_context.run()
    assert not os.path.isfile('/.autorelabel')


@pytest.mark.skipif(
    os.getenv("DESTRUCTIVE_TESTING", False) in [False, "0"],
    reason='Test disabled by default because it would modify the system',
)
def test_schedule_relabel(current_actor_context):
    current_actor_context.feed(SelinuxRelabelDecision(set_relabel=True))
    current_actor_context.run()
    assert os.path.isfile('/.autorelabel')

    # lets cleanup so we possibly not affect further testing
    os.unlink('/.autorelabel')
