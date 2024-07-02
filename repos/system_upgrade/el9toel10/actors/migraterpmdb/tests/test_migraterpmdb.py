import os.path

from leapp.models import DNFWorkaround


def test_migraterpmdb(current_actor_context):
    current_actor_context.run()
    assert len(current_actor_context.consume(DNFWorkaround)) == 1
    assert current_actor_context.consume(DNFWorkaround)[0].display_name == 'Migrate RPM DB'
    assert os.path.basename(current_actor_context.consume(DNFWorkaround)[0].script_path) == 'migraterpmdb'
    assert os.path.exists(current_actor_context.consume(DNFWorkaround)[0].script_path)
