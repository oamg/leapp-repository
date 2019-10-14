from leapp.models import SpamassassinFacts
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def test_actor_basic(current_actor_context):
    facts = SpamassassinFacts(service_overriden=False)

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)

    assert len(reports) == 4
    report = reports[0]
    assert '--ssl' in report.report['summary']
    assert 'spamc' in report.report['summary']
    report = reports[1]
    assert '--ssl-version' in report.report['summary']
    assert 'spamd' in report.report['summary']
    report = reports[2]
    assert 'spamassassin.service' in report.report['summary']
    report = reports[3]
    assert 'sa-update no longer supports SHA1' in report.report['summary']


def test_actor_no_message(current_actor_context):
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
