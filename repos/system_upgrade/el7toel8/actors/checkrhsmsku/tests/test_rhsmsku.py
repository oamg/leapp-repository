from leapp.libraries.common import rhsm
from leapp.models import Report, RHSMInfo


def test_sku_report_skipped(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setenv('LEAPP_NO_RHSM', '1')
        current_actor_context.feed(RHSMInfo(attached_skus=[]))
        current_actor_context.run()
        assert not list(current_actor_context.consume(Report))


def test_sku_report_has_skus(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setenv('LEAPP_NO_RHSM', '0')
        current_actor_context.feed(RHSMInfo(attached_skus=['testing-sku']))
        current_actor_context.run()
        assert not list(current_actor_context.consume(Report))


def test_sku_report_has_no_skus(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setenv('LEAPP_NO_RHSM', '0')
        current_actor_context.feed(RHSMInfo(attached_skus=[]))
        current_actor_context.run()
        reports = list(current_actor_context.consume(Report))
        assert reports and len(reports) == 1
        report_fields = reports[0].report
        assert report_fields['severity'] == 'high'
        assert report_fields['title'] == 'The system is not registered or subscribed.'
