import pytest

from leapp import reporting
from leapp.libraries.actor import checkgrubdefault
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import DefaultGrub, DefaultGrubInfo

_OTHER_OPTIONS = [
    DefaultGrub(name='GRUB_TIMEOUT', value='5'),
    DefaultGrub(name='GRUB_ENABLE_BLSCFG', value='true'),
]


def _default_grub_info(*grub_default_values):
    options = list(_OTHER_OPTIONS)
    options.extend(DefaultGrub(name='GRUB_DEFAULT', value=value) for value in grub_default_values)
    return DefaultGrubInfo(default_grub_info=options)


def _mock_actor(monkeypatch, msgs, arch=architecture.ARCH_X86_64):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch, msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())


@pytest.mark.parametrize('grub_default_values', [
    ('saved',),
    ('"saved"',),
    ("'saved'",),
    # the last definition wins
    ('0', 'saved'),
])
def test_no_report_when_saved_entry_is_used(monkeypatch, grub_default_values):
    _mock_actor(monkeypatch, [_default_grub_info(*grub_default_values)])

    checkgrubdefault.process()

    assert not reporting.create_report.called


@pytest.mark.parametrize('grub_default_values, expected_in_summary', [
    (('0',), 'is set to "0"'),
    (('"2"',), 'is set to "2"'),
    (('"Red Hat Enterprise Linux (4.18.0-553.el8_10.x86_64) 8.10 (Ootpa)"',),
     'is set to "Red Hat Enterprise Linux (4.18.0-553.el8_10.x86_64) 8.10 (Ootpa)"'),
    # the last definition wins
    (('saved', '1'), 'is set to "1"'),
    # empty or missing value is evaluated as 0 by GRUB
    (('',), 'is not set'),
    (('""',), 'is not set'),
    ((), 'is not set'),
])
def test_report_when_saved_entry_is_not_used(monkeypatch, grub_default_values, expected_in_summary):
    _mock_actor(monkeypatch, [_default_grub_info(*grub_default_values)])

    checkgrubdefault.process()

    assert reporting.create_report.called == 1
    report = reporting.create_report.report_fields
    assert report['title'] == 'GRUB is not configured to boot the saved default boot entry'
    assert expected_in_summary in report['summary']
    assert report['severity'] == reporting.Severity.MEDIUM
    assert reporting.Groups.BOOT in report['groups']
    # the situation must be just reported, the upgrade is possible
    assert reporting.Groups.INHIBITOR not in report['groups']


@pytest.mark.parametrize('msgs', [
    [],
    # the missing /etc/default/grub file is reported by another actor
    [DefaultGrubInfo(default_grub_info=[])],
])
def test_no_report_without_default_grub_content(monkeypatch, msgs):
    _mock_actor(monkeypatch, msgs)

    checkgrubdefault.process()

    assert not reporting.create_report.called


def test_no_report_on_s390x(monkeypatch):
    _mock_actor(monkeypatch, [_default_grub_info('0')], arch=architecture.ARCH_S390X)

    checkgrubdefault.process()

    assert not reporting.create_report.called
