import pytest

from leapp import reporting
from leapp.libraries.actor import checksystemdservicetasks
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdServicesTasks


@pytest.mark.parametrize(
    ('tasks', 'should_inhibit'),
    [
        (
            [SystemdServicesTasks(to_enable=['hello.service'], to_disable=['hello.service'])],
            True
        ),
        (
            [SystemdServicesTasks(to_enable=['hello.service', 'world.service'],
                                  to_disable=['hello.service'])],
            True
        ),
        (
            [
                SystemdServicesTasks(to_enable=['hello.service']),
                SystemdServicesTasks(to_disable=['hello.service'])
            ],
            True
        ),
        (
            [SystemdServicesTasks(to_enable=['hello.service'], to_disable=['world.service'])],
            False
        ),
        (
            [
                SystemdServicesTasks(to_enable=['hello.service']),
                SystemdServicesTasks(to_disable=['world.service'])
            ],
            False
        ),
        (
            [
                SystemdServicesTasks(to_enable=['hello.service', 'world.service']),
                SystemdServicesTasks(to_disable=['world.service', 'httpd.service'])
            ],
            True
        ),
    ]
)
def test_conflicts_detected(monkeypatch, tasks, should_inhibit):

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=tasks))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    checksystemdservicetasks.check_conflicts()

    assert bool(created_reports.called) == should_inhibit


@pytest.mark.parametrize(
    ('tasks', 'expected_reported'),
    [
        (
            [SystemdServicesTasks(to_enable=['world.service', 'httpd.service', 'hello.service'],
                                  to_disable=['hello.service', 'world.service', 'test.service'])],
            ['world.service', 'hello.service']
        ),
        (
            [
                SystemdServicesTasks(to_enable=['hello.service', 'httpd.service'],
                                     to_disable=['world.service']),
                SystemdServicesTasks(to_enable=['world.service', 'httpd.service'],
                                     to_disable=['hello.service', 'test.service'])
            ],
            ['world.service', 'hello.service']
        ),
    ]
)
def test_coflict_reported(monkeypatch, tasks, expected_reported):

    created_reports = create_report_mocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=tasks))
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    checksystemdservicetasks.check_conflicts()

    report_summary = reporting.create_report.report_fields['summary']
    assert all(service in report_summary for service in expected_reported)
