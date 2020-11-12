from leapp.snactor.fixture import current_actor_context
from leapp.models import IpaInfo
from leapp.reporting import Report


def mock_ipa_info(client, server_pkg, server_configured):
    return IpaInfo(
        has_client_package=client,
        is_client_configured=client,
        has_server_package=server_pkg,
        is_server_configured=server_configured,
    )


def test_inhibit_ipa_configured(current_actor_context):
    current_actor_context.feed(mock_ipa_info(True, True, True))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert len(reports) == 1
    fields = reports[0].report
    assert "inhibitor" in fields["groups"]
    assert "ipa-server" in fields["title"]


def test_warn_server_pkg(current_actor_context):
    current_actor_context.feed(mock_ipa_info(True, True, False))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert len(reports) == 1
    fields = reports[0].report
    assert "inhibitor" not in fields["groups"]
    assert "ipa-server" in fields["title"]


def test_client_only(current_actor_context):
    current_actor_context.feed(mock_ipa_info(True, False, False))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert not reports


def test_no_ipa(current_actor_context):
    current_actor_context.feed(mock_ipa_info(False, False, False))
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert not reports
