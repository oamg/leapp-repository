from leapp.snactor.fixture import current_actor_context
from leapp.models import RpmTransactionTasks


def test_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(RpmTransactionTasks)
    assert current_actor_context.consume(RpmTransactionTasks)[0].local_rpms
    assert not current_actor_context.consume(RpmTransactionTasks)[0].to_install
    assert not current_actor_context.consume(RpmTransactionTasks)[0].to_remove
    assert not current_actor_context.consume(RpmTransactionTasks)[0].to_keep
