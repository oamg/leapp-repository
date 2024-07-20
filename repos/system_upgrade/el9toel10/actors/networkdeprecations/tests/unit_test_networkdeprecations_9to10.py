from leapp.models import NetworkManagerConfig, Report


def test_dhcp_dhclient(current_actor_context):
    current_actor_context.feed(NetworkManagerConfig(dhcp='dhclient'))
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert len(reports) == 1
    r = reports[0].report
    assert r['title'] == 'Deprecated DHCP plugin configured'
    assert r['severity'] == 'high'


def test_dhcp_internal(current_actor_context):
    current_actor_context.feed(NetworkManagerConfig(dhcp='internal'))
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports


def test_dhcp_default(current_actor_context):
    current_actor_context.feed(NetworkManagerConfig())
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports
