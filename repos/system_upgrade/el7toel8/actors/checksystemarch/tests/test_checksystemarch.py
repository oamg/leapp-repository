import platform

from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context

def test_actor_execution(current_actor_context):
    current_actor_context.run()
    if platform.machine() == 'x86_64':
        assert not current_actor_context.consume(Report)
    else:
        assert current_actor_context.consume(Report)
        assert 'inhibitor' in current_actor_context.consume(Report)[0].flags
