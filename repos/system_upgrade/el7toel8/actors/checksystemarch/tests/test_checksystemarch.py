import platform

from leapp.models import Inhibitor
from leapp.snactor.fixture import current_actor_context

def test_actor_execution(current_actor_context):
    current_actor_context.run()
    if platform.machine() == 'x86_64':
        assert not current_actor_context.consume(Inhibitor)
    else:
        assert current_actor_context.consume(Inhibitor)
