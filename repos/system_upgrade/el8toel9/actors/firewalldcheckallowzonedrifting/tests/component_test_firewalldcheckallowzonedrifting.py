from leapp.models import FirewalldGlobalConfig, FirewallsFacts, FirewallStatus
from leapp.reporting import Report


def test_actor_firewalldcheckallowzonedrifting(current_actor_context):
    status = FirewallStatus(enabled=True, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldGlobalConfig(allowzonedrifting=True))

    current_actor_context.run()
    assert current_actor_context.consume(Report)


def test_actor_firewalldcheckallowzonedrifting_negative(current_actor_context):
    status = FirewallStatus(enabled=False, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldGlobalConfig(allowzonedrifting=True))

    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_firewalldcheckallowzonedrifting_negative2(current_actor_context):
    status = FirewallStatus(enabled=True, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldGlobalConfig(allowzonedrifting=False))

    current_actor_context.run()
    assert not current_actor_context.consume(Report)
