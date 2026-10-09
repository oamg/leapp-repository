import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import tus_inputdata
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    CustomTargetRepositoryFile,
    PkgManagerInfo,
    RepositoriesFacts,
    RHSMInfo,
    StorageInfo,
    TargetRepositories,
    TargetUserSpacePreupgradeTasks
)

_EXPECTED_DEFAULT_PKGS = {
    'dnf',
    'dnf-command(config-manager)',
    'dnf-command(download)',
    'util-linux',
}


def _setup_actor(monkeypatch, msgs, skip_rhsm=False, nogpgcheck=False):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(tus_inputdata.rhsm, 'skip_rhsm', lambda: skip_rhsm)
    monkeypatch.setattr(tus_inputdata, 'is_nogpgcheck_set', lambda: nogpgcheck)


@pytest.mark.parametrize(
    ('copy_files', 'expected_pairs'),
    [
        # Identical (src, dst) collapses into a single entry.
        (
            [CopyFile(src='/a', dst='/b'), CopyFile(src='/a', dst='/b')],
            [('/a', '/b')],
        ),
        # dst=None is a distinct key from an explicitly set dst.
        (
            [CopyFile(src='/a'), CopyFile(src='/a', dst='/a')],
            [('/a', None), ('/a', '/a')],
        ),
        # Order is preserved and multiple duplicates collapse.
        (
            [
                CopyFile(src='/a', dst='/x'),
                CopyFile(src='/b', dst='/y'),
                CopyFile(src='/a', dst='/x'),
                CopyFile(src='/b', dst='/y'),
            ],
            [('/a', '/x'), ('/b', '/y')],
        ),
    ]
)
def test_dedup_copy_files(copy_files, expected_pairs):
    result = tus_inputdata._dedup_copy_files(copy_files)
    assert [(cf.src, cf.dst) for cf in result] == expected_pairs


def test_gather_missing_rhsm_info(monkeypatch):
    _setup_actor(monkeypatch, [StorageInfo()], skip_rhsm=False)
    with pytest.raises(StopActorExecutionError) as err:
        tus_inputdata.gather()
    assert 'Missing RHSM information.' in str(err.value)


def test_gather_inconsistent_rhsm_input(monkeypatch):
    _setup_actor(monkeypatch, [StorageInfo(), RHSMInfo()], skip_rhsm=True)
    with pytest.raises(StopActorExecutionError) as err:
        tus_inputdata.gather()
    assert 'Inconsistent RHSM input.' in str(err.value)


def test_gather_missing_storage_info(monkeypatch):
    # RHSMInfo present and skip_rhsm False => hard-stops #1 and #2 pass, #3 fires.
    _setup_actor(monkeypatch, [RHSMInfo()], skip_rhsm=False)
    with pytest.raises(StopActorExecutionError) as err:
        tus_inputdata.gather()
    assert 'Missing storage information.' in str(err.value)


def test_gather_success_skip_rhsm(monkeypatch):
    storage_info = StorageInfo()
    target_repositories = TargetRepositories(rhel_repos=[], distro_repos=[])
    custom_repofile = CustomTargetRepositoryFile(file='/etc/yum.repos.d/custom.repo')
    pkg_manager_info = PkgManagerInfo()
    repositories_facts = RepositoriesFacts(repositories=[])
    tasks = TargetUserSpacePreupgradeTasks(
        install_rpms=['vim', 'dnf'],
        copy_files=[CopyFile(src='/a', dst='/b')],
    )
    msgs = [
        storage_info,
        target_repositories,
        custom_repofile,
        pkg_manager_info,
        repositories_facts,
        tasks,
    ]
    _setup_actor(monkeypatch, msgs, skip_rhsm=True, nogpgcheck=True)

    result = tus_inputdata.gather()

    assert result.storage_info is storage_info
    assert result.target_repositories is target_repositories
    assert result.rhsm_info is None
    assert result.rhui_info is None
    assert result.target_iso is None
    assert result.pkg_manager_info is pkg_manager_info
    assert result.repositories_facts is repositories_facts
    assert result.custom_repofiles == [custom_repofile]
    assert result.skip_rhsm is True
    assert result.nogpgcheck is True
    # 'dnf' is already part of the defaults, 'vim' is the only real addition.
    assert result.packages == _EXPECTED_DEFAULT_PKGS | {'vim'}
    assert [(cf.src, cf.dst) for cf in result.copy_files] == [('/a', '/b')]


def test_gather_copy_files_merged_and_deduped(monkeypatch):
    task1 = TargetUserSpacePreupgradeTasks(
        install_rpms=['pkg1'],
        copy_files=[CopyFile(src='/a', dst='/x'), CopyFile(src='/b', dst='/y')],
    )
    task2 = TargetUserSpacePreupgradeTasks(
        install_rpms=['pkg2'],
        copy_files=[CopyFile(src='/b', dst='/y'), CopyFile(src='/c', dst='/z')],
    )
    _setup_actor(monkeypatch, [StorageInfo(), task1, task2], skip_rhsm=True)

    result = tus_inputdata.gather()

    assert result.packages == _EXPECTED_DEFAULT_PKGS | {'pkg1', 'pkg2'}
    assert [(cf.src, cf.dst) for cf in result.copy_files] == [
        ('/a', '/x'), ('/b', '/y'), ('/c', '/z')
    ]


def test_gather_does_not_mutate_default_pkgs(monkeypatch):
    task = TargetUserSpacePreupgradeTasks(install_rpms=['extra-pkg'])

    _setup_actor(monkeypatch, [StorageInfo(), task], skip_rhsm=True)
    first = tus_inputdata.gather()
    assert 'extra-pkg' in first.packages

    # The module-level default must remain untouched after a gather() call.
    assert tus_inputdata._DEFAULT_INSTALL_PKGS == _EXPECTED_DEFAULT_PKGS

    # A subsequent call must not accumulate packages from the previous one.
    _setup_actor(monkeypatch, [StorageInfo()], skip_rhsm=True)
    second = tus_inputdata.gather()
    assert second.packages == _EXPECTED_DEFAULT_PKGS
