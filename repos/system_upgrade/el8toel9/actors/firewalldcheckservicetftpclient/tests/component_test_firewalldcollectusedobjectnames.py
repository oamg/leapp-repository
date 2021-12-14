from leapp.models import FirewalldUsedObjectNames
from leapp.reporting import Report


def test_actor_firewalldcheckservicetftpclient(current_actor_context):
    services = ['cockpit', 'tftp-client', 'ssh', 'https']
    policies = []
    zones = []

    current_actor_context.feed(FirewalldUsedObjectNames(services=services,
                                                        policies=policies,
                                                        zones=zones))

    current_actor_context.run()
    assert current_actor_context.consume(Report)


def test_actor_firewalldcheckservicetftpclient_negative(current_actor_context):
    services = ['cockpit', 'ssh', 'https']
    policies = []
    zones = []

    current_actor_context.feed(FirewalldUsedObjectNames(services=services,
                                                        policies=policies,
                                                        zones=zones))

    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_firewalldcheckservicetftpclient_negative2(current_actor_context):
    current_actor_context.feed(FirewalldUsedObjectNames(services=[],
                                                        policies=[],
                                                        zones=[]))

    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_firewalldcheckservicetftpclient_negative3(current_actor_context):
    current_actor_context.feed(FirewalldUsedObjectNames())

    current_actor_context.run()
    assert not current_actor_context.consume(Report)
