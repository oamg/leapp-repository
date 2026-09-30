import errno
import os

import pytest

from leapp.libraries.actor import removeresumeservice
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import api


def _setup_systemd_dir(tmpdir, with_service=True, wants_targets=()):
    systemd_dir = str(tmpdir)
    if with_service:
        tmpdir.join(removeresumeservice.SERVICE_NAME).write('')
    for target in wants_targets:
        wants_dir = tmpdir.mkdir('{}.wants'.format(target))
        wants_dir.join(removeresumeservice.SERVICE_NAME).mksymlinkto(
            os.path.join(systemd_dir, removeresumeservice.SERVICE_NAME)
        )
    return systemd_dir


def _patch_common(monkeypatch, systemd_dir, disable_called):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['systemctl', 'disable', removeresumeservice.SERVICE_NAME]
        disable_called.append(True)
        return {'exit_code': 0, 'stdout': '', 'stderr': ''}

    monkeypatch.setattr(removeresumeservice, 'SYSTEMD_DIR', systemd_dir)
    monkeypatch.setattr(removeresumeservice, 'run', mocked_run)
    monkeypatch.setattr(removeresumeservice, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())


def test_missing_wants_symlink_is_not_logged(monkeypatch, tmpdir):
    """systemctl disable already removed the wants link; unlink must not log ENOENT."""
    systemd_dir = _setup_systemd_dir(tmpdir, with_service=True, wants_targets=())
    disable_called = []
    _patch_common(monkeypatch, systemd_dir, disable_called)

    removeresumeservice.process()

    assert disable_called
    assert not os.path.isfile(os.path.join(systemd_dir, removeresumeservice.SERVICE_NAME))
    assert not any('Failed removing' in msg for msg in api.current_logger.dbgmsg)
    assert removeresumeservice.create_report.called == 1


@pytest.mark.parametrize('target', removeresumeservice.WANTS_TARGETS)
def test_leftover_wants_symlink_is_removed(monkeypatch, tmpdir, target):
    systemd_dir = _setup_systemd_dir(tmpdir, with_service=True, wants_targets=(target,))
    wants_path = os.path.join(
        systemd_dir, '{}.wants'.format(target), removeresumeservice.SERVICE_NAME
    )
    assert os.path.lexists(wants_path)
    disable_called = []
    _patch_common(monkeypatch, systemd_dir, disable_called)

    removeresumeservice.process()

    assert disable_called
    assert not os.path.lexists(wants_path)
    assert not os.path.isfile(os.path.join(systemd_dir, removeresumeservice.SERVICE_NAME))
    assert not any('Failed removing' in msg for msg in api.current_logger.dbgmsg)


def test_no_service_file_skips_disable(monkeypatch, tmpdir):
    systemd_dir = _setup_systemd_dir(tmpdir, with_service=False)
    disable_called = []
    _patch_common(monkeypatch, systemd_dir, disable_called)

    removeresumeservice.process()

    assert not disable_called
    assert removeresumeservice.create_report.called == 1


def test_unlink_other_oserror_is_raised(monkeypatch, tmpdir):
    systemd_dir = _setup_systemd_dir(tmpdir, with_service=True)
    disable_called = []
    _patch_common(monkeypatch, systemd_dir, disable_called)

    def mocked_unlink(path):
        raise OSError(errno.EACCES, 'Permission denied', path)

    monkeypatch.setattr(os, 'unlink', mocked_unlink)

    with pytest.raises(OSError) as excinfo:
        removeresumeservice.process()
    assert excinfo.value.errno == errno.EACCES
    assert any('Failed removing' in msg for msg in api.current_logger.dbgmsg)
