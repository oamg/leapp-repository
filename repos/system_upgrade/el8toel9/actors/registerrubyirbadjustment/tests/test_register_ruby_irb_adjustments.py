import os.path

from leapp.models import DNFWorkaround


def test_register_ruby_irb_adjustments(current_actor_context):
    current_actor_context.run()
    assert len(current_actor_context.consume(DNFWorkaround)) == 1
    assert current_actor_context.consume(DNFWorkaround)[0].display_name == 'IRB directory fix'
    assert os.path.basename(current_actor_context.consume(DNFWorkaround)[0].script_path) == 'handlerubyirbsymlink'
    assert os.path.exists(current_actor_context.consume(DNFWorkaround)[0].script_path)
