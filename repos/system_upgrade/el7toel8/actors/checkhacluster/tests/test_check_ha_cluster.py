from leapp.reporting import Report
from leapp.libraries.actor.library import COROSYNC_CONF_LOCATION


def assert_inhibits(reports, node_type):
    assert len(reports) == 1
    assert "inhibitor" in reports[0].flags
    assert "cluster {0}".format(node_type) in reports[0].detail["summary"]


def test_no_inhibit_when_no_ha_cluster(monkeypatch, current_actor_context):
    monkeypatch.setattr("os.path.isfile", lambda path: False)
    current_actor_context.run()
    assert len(current_actor_context.consume(Report)) == 0


def test_inhibits_when_cluster_node(monkeypatch, current_actor_context):
    monkeypatch.setattr("os.path.isfile", lambda path: True)
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
    monkeypatch.setattr(
        "os.path.isfile",
        lambda path: path != COROSYNC_CONF_LOCATION
    )
    current_actor_context.run()
    assert_inhibits(current_actor_context.consume(Report), "remote node")
