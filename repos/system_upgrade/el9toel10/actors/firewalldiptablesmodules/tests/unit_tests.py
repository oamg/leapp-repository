from leapp.models import (
    FirewalldDirectConfig,
    FirewalldGlobalConfig,
    FirewallsFacts,
    FirewallStatus,
    RpmTransactionTasks
)


def test_produce(current_actor_context):
    status = FirewallStatus(enabled=True, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldGlobalConfig(firewallbackend='iptables'))
    current_actor_context.run()
    assert current_actor_context.consume(RpmTransactionTasks)[0].to_install[0] == 'kernel-modules-extra'


def test_produce_02(current_actor_context):
    status = FirewallStatus(enabled=True, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldDirectConfig(has_permanent_configuration=True))
    current_actor_context.run()
    assert current_actor_context.consume(RpmTransactionTasks)[0].to_install[0] == 'kernel-modules-extra'


def test_no_produce_negative(current_actor_context):
    current_actor_context.feed(FirewalldGlobalConfig())
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)


def test_no_produce_negative_02(current_actor_context):
    status = FirewallStatus(enabled=False, active=True)
    current_actor_context.feed(FirewallsFacts(firewalld=status,
                                              iptables=status,
                                              ip6tables=status))
    current_actor_context.feed(FirewalldGlobalConfig(firewallbackend='iptables'))
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)


def test_no_produce_negative_03(current_actor_context):
    current_actor_context.feed(FirewalldDirectConfig())
    current_actor_context.run()
    assert not current_actor_context.consume(RpmTransactionTasks)
