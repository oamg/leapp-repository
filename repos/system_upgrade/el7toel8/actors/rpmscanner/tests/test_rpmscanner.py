import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import InstalledRPM


@pytest.mark.skip(reason="skipping on py3 raise error on snactor")
def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(InstalledRPM)
    assert current_actor_context.consume(InstalledRPM)[0].items
