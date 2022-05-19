from leapp.models import CryptoPolicyInfo


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(CryptoPolicyInfo)
