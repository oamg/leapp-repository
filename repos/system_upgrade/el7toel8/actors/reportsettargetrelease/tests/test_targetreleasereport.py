from leapp.models import Report, TargetRHSMInfo


def test_report_target_version(current_actor_context):
    current_actor_context.feed(TargetRHSMInfo(release='6.6.6'))
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    assert '6.6.6' in reports[0].detail.get('summary', '')
    assert '6.6.6' in reports[0].title


def test_report_target_version_notset(current_actor_context):
    current_actor_context.feed(TargetRHSMInfo(release=''))
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports


def test_report_target_version_nomessage(current_actor_context):
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports
