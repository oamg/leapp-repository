import pytest

from leapp.libraries.actor import cleanupbootloaderentries
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import MachineIdInfo

_MACHINE_ID = '1485ef58ae5a41f1a109b2ae85e22374'
_OLD_MACHINE_ID = 'ff1165e69b5a4fa18d2bb47c8a8a51e6'

# Stale entries named after the old machine ID; expected to be removed.
_OLD_ENTRIES = [
    '/boot/loader/entries/{}-0-rescue.conf'.format(_OLD_MACHINE_ID),
    '/boot/loader/entries/{}-5.14.0-687.el9_8.x86_64.conf'.format(_OLD_MACHINE_ID),
]

# Entries named after the current machine ID; expected to be kept.
_NEW_ENTRIES = [
    '/boot/loader/entries/{}-5.14.0-999.el9.x86_64.conf'.format(_MACHINE_ID),
]

_ENTRIES = _OLD_ENTRIES + _NEW_ENTRIES


class _FakeFile:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._content


def _setup(monkeypatch, entries, machine_id=_MACHINE_ID, original_machine_id=None,
           src_distro='ol', dst_distro='rhel'):
    """
    Mock the actor context for cleanupbootloaderentries.process().

    :param entries: boot loader entry paths returned by the mocked glob.glob
    :param machine_id: value returned by the mocked _read_machine_id (None to simulate a read failure)
    :param original_machine_id: machine ID from the consumed MachineIdInfo (None means no such message)
    :param src_distro: source distro ID (differs from dst_distro to simulate a conversion)
    :param dst_distro: target distro ID
    :returns: (report_mock, removed, logger) where removed collects paths passed to os.remove
    """
    msgs = [] if original_machine_id is None else [MachineIdInfo(machine_id=original_machine_id)]
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(src_distro=src_distro, dst_distro=dst_distro, msgs=msgs))
    logger = logger_mocked()
    monkeypatch.setattr(api, 'current_logger', logger)
    report_mock = create_report_mocked()
    monkeypatch.setattr(cleanupbootloaderentries.reporting, 'create_report', report_mock)

    removed = []
    monkeypatch.setattr(cleanupbootloaderentries.glob, 'glob', lambda pattern: list(entries))
    monkeypatch.setattr(cleanupbootloaderentries.os, 'remove', removed.append)
    monkeypatch.setattr(cleanupbootloaderentries, '_read_machine_id', lambda: machine_id)
    return report_mock, removed, logger


def test_removes_only_non_matching_entries(monkeypatch):
    report_mock, removed, _ = _setup(monkeypatch, _ENTRIES)

    cleanupbootloaderentries.process()

    assert removed == _OLD_ENTRIES
    assert report_mock.called == 1
    summary = report_mock.report_fields['summary']
    assert _MACHINE_ID in summary
    assert all(entry in summary for entry in _OLD_ENTRIES)
    assert all(entry not in summary for entry in _NEW_ENTRIES)


@pytest.mark.parametrize('original_machine_id,expect_logged', [
    (_OLD_MACHINE_ID, True),   # machine ID changed during the upgrade
    (_MACHINE_ID, False),      # machine ID unchanged
    (None, False),             # no MachineIdInfo message consumed
], ids=['changed', 'unchanged', 'no_machineidinfo'])
def test_machine_id_change_logging(monkeypatch, original_machine_id, expect_logged):
    _, _, logger = _setup(monkeypatch, _ENTRIES, original_machine_id=original_machine_id)

    cleanupbootloaderentries.process()

    logged = any('machine ID changed' in msg for msg in logger.infomsg)
    assert logged == expect_logged
    if expect_logged:
        assert any(_MACHINE_ID in msg and _OLD_MACHINE_ID in msg for msg in logger.infomsg)


@pytest.mark.parametrize('setup_kwargs', [
    {'entries': _ENTRIES, 'src_distro': 'rhel', 'dst_distro': 'rhel'},  # not a conversion
    {'entries': _NEW_ENTRIES},                                          # all entries match current machine ID
    {'entries': _ENTRIES, 'machine_id': None},                          # machine ID unreadable
    {'entries': _ENTRIES, 'machine_id': ''},                            # machine ID empty
], ids=['no_stale_entries', 'not_converting', 'machine_id_unreadable', 'machine_id_empty'])
def test_no_entries_removed(monkeypatch, setup_kwargs):
    report_mock, removed, _ = _setup(monkeypatch, **setup_kwargs)

    cleanupbootloaderentries.process()

    assert not removed
    assert report_mock.called == 0


def test_continues_when_removal_fails(monkeypatch):
    report_mock, removed, _ = _setup(monkeypatch, _ENTRIES)

    def fake_remove(path):
        if path == _OLD_ENTRIES[0]:
            raise OSError('permission denied')
        removed.append(path)

    monkeypatch.setattr(cleanupbootloaderentries.os, 'remove', fake_remove)

    cleanupbootloaderentries.process()

    # _OLD_ENTRIES[0] failed to be removed, _OLD_ENTRIES[1] still removed
    assert removed == [_OLD_ENTRIES[1]]
    assert report_mock.called == 1
    assert _OLD_ENTRIES[1] in report_mock.report_fields['summary']
    assert _OLD_ENTRIES[0] not in report_mock.report_fields['summary']


@pytest.mark.parametrize('content,expected', [
    ('{}\n'.format(_MACHINE_ID), _MACHINE_ID),
    (_MACHINE_ID, _MACHINE_ID),
    ('', ''),
    ('\n', ''),
])
def test_read_machine_id(monkeypatch, content, expected):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(cleanupbootloaderentries, 'open',
                        lambda *a, **k: _FakeFile(content), raising=False)
    assert cleanupbootloaderentries._read_machine_id() == expected


def test_read_machine_id_unreadable(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def _raise(*a, **k):
        raise OSError('no such file')

    monkeypatch.setattr(cleanupbootloaderentries, 'open', _raise, raising=False)
    assert cleanupbootloaderentries._read_machine_id() is None
