import os.path

from leapp.models import DNFWorkaround
from leapp.snactor.fixture import current_actor_context


def test_register_yum_adjustments(current_actor_context):
    current_actor_context.run()
    assert len(current_actor_context.consume(DNFWorkaround)) == 1
    assert current_actor_context.consume(DNFWorkaround)[0].display_name == 'yum config fix'
    assert os.path.basename(current_actor_context.consume(DNFWorkaround)[0].script_path) == 'handleyumconfig'
    assert os.path.exists(current_actor_context.consume(DNFWorkaround)[0].script_path)
