import pytest

from leapp.models import IfCfg, NetworkManagerConfig, Report
from leapp.utils.report import is_inhibitor


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


def test_ifcfg(current_actor_context):
    """
    Report when a file ready for migration is present.
    """

    current_actor_context.feed(IfCfg(filename='/NM/ifcfg-eth-dev'))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 1
    report_fields = reports[0].report
    assert is_inhibitor(report_fields)
    assert report_fields['title'] == 'Legacy network configuration found'
    resources = report_fields['detail']['related_resources']
    assert len(resources) == 2
    assert resources[0]['scheme'] == 'package'
    assert resources[0]['title'] == 'NetworkManager'
    assert resources[1]['scheme'] == 'file'
    assert resources[1]['title'] == '/NM/ifcfg-eth-dev'


@pytest.mark.parametrize('files',
                         [('/NM/rule-lost',),
                          ('/NM/route6-eth-dev', '/NM/rule-eth-dev')])
def test_leftovers(current_actor_context, files):
    """
    Report when what appears like artifacts from unsuccessful migration are present.
    """

    for file in files:
        current_actor_context.feed(IfCfg(filename=file))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 1
    report_fields = reports[0].report
    assert is_inhibitor(report_fields)
    assert report_fields['title'] == 'Unused legacy network configuration found'
    resources = report_fields['detail']['related_resources']
    assert len(resources) == len(files)
    for i in range(len(files)):
        assert resources[i]['scheme'] == 'file'
        assert resources[i]['title'] == files[i]


@pytest.mark.parametrize('files',
                         [('/NM/ifcfg-old', '/NM/rule-old'),
                          ('/NM/ifcfg-old', '/NM/rule6-old'),
                          ('/NM/ifcfg-old', '/NM/rule6-old', '/NM/rule-old')])
def test_rules(current_actor_context, files):
    """
    Report when configuration that requires manual migration is present.
    """

    for file in files:
        current_actor_context.feed(IfCfg(filename=file))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert len(reports) == 1
    report_fields = reports[0].report
    assert is_inhibitor(report_fields)
    assert report_fields['title'] == 'Legacy network configuration with policy routing rules found'
    resources = report_fields['detail']['related_resources']
    assert len(resources) == 2 + len(files)
    assert resources[0]['scheme'] == 'package'
    assert resources[0]['title'] == 'NetworkManager'
    assert resources[1]['scheme'] == 'package'
    assert resources[1]['title'] == 'NetworkManager-dispatcher-routing-rules'
    for i in range(len(files)):
        assert resources[2 + i]['scheme'] == 'file'
        assert resources[2 + i]['title'] == files[i]
