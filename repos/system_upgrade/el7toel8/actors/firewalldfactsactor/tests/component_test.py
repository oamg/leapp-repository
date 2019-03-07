from leapp.models import FirewalldFacts


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(FirewalldFacts)
