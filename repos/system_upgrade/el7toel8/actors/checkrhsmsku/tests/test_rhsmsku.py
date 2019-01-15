from leapp.libraries.common import rhsm
from leapp.models import Report, SourceRHSMInfo


def test_sku_report_skipped(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setattr(rhsm, 'skip_rhsm', lambda: True)
        current_actor_context.run()
        assert not list(current_actor_context.consume(Report))


def test_sku_report_has_skus(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setattr(rhsm, 'skip_rhsm', lambda: True)
        current_actor_context.feed(SourceRHSMInfo(attached_skus=['testing-sku']))
        current_actor_context.run()
        assert not list(current_actor_context.consume(Report))


def test_sku_report_has_no_skus(monkeypatch, current_actor_context):
    with monkeypatch.context() as context:
        context.setattr(rhsm, 'skip_rhsm', lambda: True)
        current_actor_context.feed(SourceRHSMInfo(attached_skus=[]))
        current_actor_context.run()
        reports = list(current_actor_context.consume(Report))
        assert reports and len(reports) == 1
        assert reports[0].severity == 'high'
        assert reports[0].title == 'The system is not registered or subscribed.'
