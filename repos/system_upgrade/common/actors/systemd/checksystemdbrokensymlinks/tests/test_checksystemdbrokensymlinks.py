import pytest

from leapp import reporting
from leapp.libraries.actor import checksystemdbrokensymlinks
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdBrokenSymlinksSource, SystemdServiceFile, SystemdServicesInfoSource


def test_report_broken_symlinks(monkeypatch):

    symlinks = [
        '/etc/systemd/system/multi-user.target.wants/hello.service',
        '/etc/systemd/system/multi-user.target.wants/world.service',
    ]

    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    checksystemdbrokensymlinks._report_broken_symlinks(symlinks)

    assert created_reports.called
    assert all([s in created_reports.report_fields['summary'] for s in symlinks])


def test_report_enabled_services_broken_symlinks(monkeypatch):
    symlinks = [
        '/etc/systemd/system/multi-user.target.wants/foo.service',
        '/etc/systemd/system/multi-user.target.wants/bar.service',
    ]

    created_reports = create_report_mocked()
    monkeypatch.setattr(reporting, 'create_report', created_reports)

    checksystemdbrokensymlinks._report_enabled_services_broken_symlinks(symlinks)

    assert created_reports.called
    assert all([s in created_reports.report_fields['summary'] for s in symlinks])


class ReportBrokenSymlinks(object):
    def __init__(self):
        self.symlinks = []

    def __call__(self, unit, *args, **kwargs):
        self.symlinks.append(unit)
        return {}


def test_broken_symlinks_reported(monkeypatch):
    broken_symlinks = SystemdBrokenSymlinksSource(broken_symlinks=[
        '/etc/systemd/system/multi-user.target.wants/foo.service',
        '/etc/systemd/system/multi-user.target.wants/bar.service',
        '/etc/systemd/system/multi-user.target.wants/hello.service',
        '/etc/systemd/system/multi-user.target.wants/world.service',
    ])
    systemd_services = SystemdServicesInfoSource(service_files=[
        SystemdServiceFile(name='foo.service', state='enabled'),
        SystemdServiceFile(name='bar.service', state='enabled'),
        SystemdServiceFile(name='hello.service', state='disabled'),
    ])
    broken = []
    enabled_broken = []

    def _report_broken_symlinks_mocked(symlinks):
        broken.extend(symlinks)

    def _report_enabled_services_broken_symlinks_mocked(symlinks):
        enabled_broken.extend(symlinks)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[broken_symlinks, systemd_services]))
    monkeypatch.setattr(checksystemdbrokensymlinks, '_report_broken_symlinks', _report_broken_symlinks_mocked)
    monkeypatch.setattr(
        checksystemdbrokensymlinks,
        '_report_enabled_services_broken_symlinks',
        _report_enabled_services_broken_symlinks_mocked
    )

    checksystemdbrokensymlinks.process()

    assert broken == [
        '/etc/systemd/system/multi-user.target.wants/hello.service',
        '/etc/systemd/system/multi-user.target.wants/world.service',
    ]

    assert enabled_broken == [
        '/etc/systemd/system/multi-user.target.wants/foo.service',
        '/etc/systemd/system/multi-user.target.wants/bar.service',
    ]
