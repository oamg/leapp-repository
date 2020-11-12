from leapp.reporting import Report
from leapp.libraries.actor.checkhacluster import COROSYNC_CONF_LOCATION, CIB_LOCATION


def assert_inhibits(reports, node_type):
    assert len(reports) == 1
    report_fields = reports[0].report
    assert "inhibitor" in report_fields['groups']
    assert "cluster {0}".format(node_type) in report_fields["summary"]


def test_no_inhibit_when_no_ha_cluster(monkeypatch, current_actor_context):
    monkeypatch.setattr("os.path.isfile", lambda path: False)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_inhibits_when_cluster_node(monkeypatch, current_actor_context):
    # NOTE(ivasilev) Limiting here the paths to mock not to cause unexpected side-effects
    # (original test had path: True)
    monkeypatch.setattr("os.path.isfile", lambda path: path in [COROSYNC_CONF_LOCATION, CIB_LOCATION])
    current_actor_context.run()
    assert_inhibits(current_actor_context.consume(Report), "node")


def test_inhibits_when_cluster_node_no_cib(monkeypatch, current_actor_context):
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: path == COROSYNC_CONF_LOCATION
    )
    current_actor_context.run()
    assert_inhibits(current_actor_context.consume(Report), "node")


def test_inhibits_when_cluster_remote_node(monkeypatch, current_actor_context):
    # NOTE(ivasilev) Limiting here the paths to mock not to cause unexpected side-effects
    # (original test had path: path != COROSYNC_CONF_LOCATION)
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: path == CIB_LOCATION
    )
    current_actor_context.run()
    assert_inhibits(current_actor_context.consume(Report), "remote node")
