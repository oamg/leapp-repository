import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_inputdata
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, RHSMInfo, StorageInfo, TargetUserSpacePreupgradeTasks

_DEFAULTS = tus_inputdata._DEFAULT_INSTALL_PKGS


def _setup(monkeypatch, msgs, skip_rhsm=False, nogpgcheck=False):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(tus_inputdata.rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(tus_inputdata, 'is_nogpgcheck_set', lambda: nogpgcheck)


def test_gather_happy_path_with_rhsm(monkeypatch):
    msgs = [StorageInfo(), RHSMInfo(existing_product_certificates=[])]
    _setup(monkeypatch, msgs, skip_rhsm=False)

    inputs = tus_inputdata.gather()

    assert inputs.storage_info is not None
    assert inputs.rhsm_info is not None
    assert inputs.skip_rhsm is False
    assert inputs.nogpgcheck is False
    # Default packages always present, nothing extra requested.
    assert inputs.packages == _DEFAULTS
    assert inputs.copy_files == []


def test_gather_happy_path_skip_rhsm(monkeypatch):
    _setup(monkeypatch, [StorageInfo()], skip_rhsm=True)

    inputs = tus_inputdata.gather()

    assert inputs.rhsm_info is None
    assert inputs.skip_rhsm is True


def test_gather_hardstop_missing_rhsm(monkeypatch):
    # #1: no RHSMInfo and RHSM not being skipped.
    _setup(monkeypatch, [StorageInfo()], skip_rhsm=False)

    with pytest.raises(StopActorExecutionError):
        tus_inputdata.gather()


def test_gather_hardstop_inconsistent_rhsm(monkeypatch):
    # #2: RHSM skipped but RHSMInfo present.
    msgs = [StorageInfo(), RHSMInfo(existing_product_certificates=[])]
    _setup(monkeypatch, msgs, skip_rhsm=True)

    with pytest.raises(StopActorExecutionError):
        tus_inputdata.gather()


def test_gather_hardstop_missing_storage(monkeypatch):
    # #3: no StorageInfo.
    _setup(monkeypatch, [RHSMInfo(existing_product_certificates=[])], skip_rhsm=False)

    with pytest.raises(StopActorExecutionError):
        tus_inputdata.gather()


def test_gather_merges_install_rpms(monkeypatch):
    tasks = TargetUserSpacePreupgradeTasks(install_rpms=['vim', 'git'], copy_files=[])
    _setup(monkeypatch, [StorageInfo(), tasks], skip_rhsm=True)

    inputs = tus_inputdata.gather()

    assert inputs.packages == _DEFAULTS | {'vim', 'git'}


def test_gather_merges_multiple_preupgrade_tasks(monkeypatch):
    # The actor accepts multiple TargetUserSpacePreupgradeTasks messages.
    tasks_a = TargetUserSpacePreupgradeTasks(install_rpms=['vim'],
                                             copy_files=[CopyFile(src='/a', dst='/x')])
    tasks_b = TargetUserSpacePreupgradeTasks(install_rpms=['git'],
                                             copy_files=[CopyFile(src='/b', dst='/y')])
    _setup(monkeypatch, [StorageInfo(), tasks_a, tasks_b], skip_rhsm=True)

    inputs = tus_inputdata.gather()

    assert inputs.packages == _DEFAULTS | {'vim', 'git'}
    assert [(cf.src, cf.dst) for cf in inputs.copy_files] == [('/a', '/x'), ('/b', '/y')]


def test_gather_dedups_copy_files(monkeypatch):
    copy_files = [
        CopyFile(src='/a', dst='/x'),
        CopyFile(src='/a', dst='/x'),   # exact duplicate -> dropped
        CopyFile(src='/a', dst='/y'),   # same src, different dst -> kept
        CopyFile(src='/b', dst=None),
        CopyFile(src='/b', dst=None),   # duplicate with null dst -> dropped
    ]
    tasks = TargetUserSpacePreupgradeTasks(install_rpms=[], copy_files=copy_files)
    _setup(monkeypatch, [StorageInfo(), tasks], skip_rhsm=True)

    inputs = tus_inputdata.gather()

    pairs = [(cf.src, cf.dst) for cf in inputs.copy_files]
    assert pairs == [('/a', '/x'), ('/a', '/y'), ('/b', None)]


def test_gather_nogpgcheck_flag(monkeypatch):
    _setup(monkeypatch, [StorageInfo()], skip_rhsm=True, nogpgcheck=True)

    inputs = tus_inputdata.gather()

    assert inputs.nogpgcheck is True


def test_gather_does_not_mutate_default_packages(monkeypatch):
    # Regression: gather() must not accumulate packages into the shared default.
    tasks = TargetUserSpacePreupgradeTasks(install_rpms=['extra-pkg'], copy_files=[])
    _setup(monkeypatch, [StorageInfo(), tasks], skip_rhsm=True)

    tus_inputdata.gather()

    assert 'extra-pkg' not in tus_inputdata._DEFAULT_INSTALL_PKGS
