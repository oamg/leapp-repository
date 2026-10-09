import pytest

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import tus_targetrepos
from leapp.libraries.common import repofileutils
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    DistroTargetRepository,
    RepositoriesFactsTarget,
    RepositoryData,
    RepositoryFile,
    RHELTargetRepository,
    TargetRepositories,
    UsedTargetRepositories
)
from leapp.utils.deprecation import suppress_deprecation

_BASE = ['baseos', 'appstream']


class _Inputs:
    def __init__(self, target_repositories, rhui_info=None, skip_rhsm=False):
        self.target_repositories = target_repositories
        self.rhui_info = rhui_info
        self.skip_rhsm = skip_rhsm


class _Repo:
    def __init__(self, repoid):
        self.repoid = repoid


class _RepoFile:
    def __init__(self, repoids):
        self.data = [_Repo(repoid) for repoid in repoids]


def _parsed(*repofiles_repoids):
    """Build a fake get_parsed_repofiles() result; one _RepoFile per argument."""
    return [_RepoFile(repoids) for repoids in repofiles_repoids]


@suppress_deprecation(RHELTargetRepository)
def _target_repos(distro=None, rhel=None, custom=None):
    return TargetRepositories(
        distro_repos=[DistroTargetRepository(repoid=r) for r in (distro or [])],
        rhel_repos=[RHELTargetRepository(repoid=r) for r in (rhel or [])],
        custom_repos=[CustomTargetRepository(repoid=r) for r in (custom or [])],
    )


def _patch(monkeypatch, reports, distro_repoids=(), rhui_repoids=(), parsed=None,
           parsed_exc=None, src_distro='rhel', src_ver='8.10', dst_distro='rhel', dst_ver='9.6'):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_distro=src_distro, dst_distro=dst_distro, src_ver=src_ver, dst_ver=dst_ver))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(tus_targetrepos.distro, 'get_target_distro_repoids',
                        lambda ctx: list(distro_repoids))
    monkeypatch.setattr(tus_targetrepos.tus_rhui, 'discover_client_exposed_repoids',
                        lambda ctx, ri, tv: set(rhui_repoids))

    def _get_parsed(ctx):
        if parsed_exc is not None:
            raise parsed_exc
        return parsed if parsed is not None else []

    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles', _get_parsed)
    monkeypatch.setattr(tus_targetrepos.reporting, 'create_report', reports.append)


def _titles(reports):
    return [part.value for parts in reports for part in parts
            if type(part).__name__ == 'Title']


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def test_requested_distro_repoids_merges_rhel_repos():
    target_repos = _target_repos(distro=['d1'], rhel=['r1'])
    assert tus_targetrepos._requested_distro_repoids(target_repos) == {'d1', 'r1'}


@pytest.mark.parametrize('repoids,expected', [
    ({'rhel-9-BaseOS', 'rhel-9-AppStream'}, True),
    ({'rhel-9-baseos'}, False),
    ({'rhel-9-appstream'}, False),
    (set(), False),
])
def test_has_base_repos(repoids, expected):
    assert tus_targetrepos._has_base_repos(repoids) is expected


def test_duplicate_repoids_detects_cross_file_duplicates(monkeypatch):
    # 'baseos' appears in two repofiles -> duplicate; 'appstream' only once.
    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles',
                        lambda ctx: _parsed(['baseos', 'appstream'], ['baseos', 'extra']))
    assert tus_targetrepos._duplicate_repoids(None) == {'baseos'}


def test_duplicate_repoids_none_when_unique(monkeypatch):
    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles',
                        lambda ctx: _parsed(['baseos'], ['appstream']))
    assert tus_targetrepos._duplicate_repoids(None) == set()


@pytest.mark.parametrize('kwargs,skip_rhsm,expected', [
    # default: RHEL->RHEL, not CS8, RHSM active -> applies
    ({}, False, True),
    # conversion (source distro != target distro) -> skipped
    ({'src_distro': 'almalinux', 'dst_distro': 'rhel', 'src_ver': '9.6'}, False, False),
    # source CentOS Stream 8 -> skipped
    ({'src_distro': 'centos', 'dst_distro': 'centos', 'src_ver': '8.10'}, False, False),
    # RHEL target with RHSM skipped -> skipped
    ({}, True, False),
    # non-RHEL target with RHSM active -> applies
    ({'src_distro': 'centos', 'dst_distro': 'centos', 'src_ver': '9.6', 'dst_ver': '10.0'}, False, True),
])
def test_base_repo_check_applies(monkeypatch, kwargs, skip_rhsm, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_distro=kwargs.get('src_distro', 'rhel'),
        dst_distro=kwargs.get('dst_distro', 'rhel'),
        src_ver=kwargs.get('src_ver', '8.10'),
        dst_ver=kwargs.get('dst_ver', '9.6'),
    ))
    assert tus_targetrepos._base_repo_check_applies(skip_rhsm) is expected


# --------------------------------------------------------------------------- #
# select_target_repositories - happy paths
# --------------------------------------------------------------------------- #
def test_select_happy_path(monkeypatch):
    reports = []
    _patch(monkeypatch, reports, distro_repoids=_BASE, parsed=_parsed(_BASE))
    inputs = _Inputs(_target_repos(distro=_BASE))

    result = tus_targetrepos.select_target_repositories(None, inputs)

    assert isinstance(result, UsedTargetRepositories)
    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos']
    assert not reports


def test_select_includes_rhui_repoids(monkeypatch):
    reports = []
    # skip_rhsm + RHEL target -> base-repo check does not apply.
    _patch(monkeypatch, reports,
           distro_repoids=[],
           rhui_repoids=['rhui-baseos', 'rhui-appstream'],
           parsed=_parsed(['rhui-baseos', 'rhui-appstream']))
    inputs = _Inputs(_target_repos(distro=['rhui-baseos', 'rhui-appstream']),
                     rhui_info=object(), skip_rhsm=True)

    result = tus_targetrepos.select_target_repositories(None, inputs)

    assert sorted(r.repoid for r in result.repos) == ['rhui-appstream', 'rhui-baseos']


def test_select_custom_repo_selected_from_available(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=_BASE,
           parsed=_parsed(_BASE + ['custom1']))
    inputs = _Inputs(_target_repos(distro=_BASE, custom=['custom1']))

    result = tus_targetrepos.select_target_repositories(None, inputs)

    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos', 'custom1']
    assert not reports


# --------------------------------------------------------------------------- #
# Inhibitor #2 - duplicates (reports but does NOT stop; only when skip_rhsm)
# --------------------------------------------------------------------------- #
def test_inhibit_duplicates_when_skip_rhsm_reports_without_stopping(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=_BASE,
           parsed=_parsed(_BASE, ['baseos']),   # baseos duplicated across files
           dst_distro='rhel')
    inputs = _Inputs(_target_repos(distro=_BASE), skip_rhsm=True)

    result = tus_targetrepos.select_target_repositories(None, inputs)

    # The duplicate inhibitor is raised as a report, but selection still succeeds.
    assert 'A YUM/DNF repository defined multiple times' in _titles(reports)
    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos']


def test_no_duplicate_check_without_skip_rhsm(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=_BASE,
           parsed=_parsed(_BASE, ['baseos']))   # duplicate present but RHSM active
    inputs = _Inputs(_target_repos(distro=_BASE), skip_rhsm=False)

    result = tus_targetrepos.select_target_repositories(None, inputs)

    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos']
    assert not reports


# --------------------------------------------------------------------------- #
# Inhibitor #3 - missing base repos + skip conditions
# --------------------------------------------------------------------------- #
def test_inhibit_missing_base_repos(monkeypatch):
    reports = []
    _patch(monkeypatch, reports, distro_repoids=['foo'], parsed=_parsed(['foo']))
    inputs = _Inputs(_target_repos(distro=['foo']))

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'Cannot find required basic target OS repositories.' in _titles(reports)


def test_base_repo_check_skipped_for_conversion(monkeypatch):
    reports = []
    # almalinux -> rhel is a conversion, so the base-repo check is skipped.
    _patch(monkeypatch, reports, distro_repoids=['foo'], parsed=_parsed(['foo']),
           src_distro='almalinux', dst_distro='rhel', src_ver='9.6')
    inputs = _Inputs(_target_repos(distro=['foo']))

    result = tus_targetrepos.select_target_repositories(None, inputs)
    assert [r.repoid for r in result.repos] == ['foo']
    assert not reports


# --------------------------------------------------------------------------- #
# Inhibitor #4 - no enabled target repos
# --------------------------------------------------------------------------- #
def test_inhibit_no_enabled_repos(monkeypatch):
    reports = []
    # skip_rhsm + RHEL target -> base check skipped; nothing discovered/available.
    _patch(monkeypatch, reports, distro_repoids=[], parsed=[])
    inputs = _Inputs(_target_repos(distro=['foo']), skip_rhsm=True)

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'There are no enabled target repositories' in _titles(reports)


# --------------------------------------------------------------------------- #
# Inhibitor #5 - missing custom repos
# --------------------------------------------------------------------------- #
def test_inhibit_missing_custom_repos(monkeypatch):
    reports = []
    _patch(monkeypatch, reports, distro_repoids=_BASE, parsed=_parsed(_BASE))
    inputs = _Inputs(_target_repos(distro=_BASE, custom=['custom1']))

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'Some required custom target repositories have not been found' in _titles(reports)


# --------------------------------------------------------------------------- #
# Error path - invalid repofile while collecting available repoids
# --------------------------------------------------------------------------- #
def test_select_hard_stops_on_invalid_repofile(monkeypatch):
    reports = []
    exc = repofileutils.InvalidRepoDefinition('bad', repofile='/etc/yum.repos.d/x.repo', repoid='x')
    _patch(monkeypatch, reports, distro_repoids=_BASE, parsed_exc=exc)
    inputs = _Inputs(_target_repos(distro=_BASE))

    with pytest.raises(StopActorExecutionError):
        tus_targetrepos.select_target_repositories(None, inputs)


# --------------------------------------------------------------------------- #
# Snapshot builder
# --------------------------------------------------------------------------- #
def test_build_snapshot(monkeypatch):
    parsed = [RepositoryFile(file='/etc/yum.repos.d/redhat.repo', data=[
        RepositoryData(repoid='baseos', name='BaseOS', additional_fields='{"gpgkey": "x"}'),
    ])]
    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles', lambda ctx: parsed)

    snapshot = tus_targetrepos.build_target_repositories_snapshot(None)

    assert isinstance(snapshot, RepositoriesFactsTarget)
    assert [rf.file for rf in snapshot.repositories] == ['/etc/yum.repos.d/redhat.repo']
    # additional_fields (gpg data) preserved for missinggpgkeysinhibitor.
    assert snapshot.repositories[0].data[0].additional_fields == '{"gpgkey": "x"}'


def test_build_snapshot_hard_stops_on_invalid_repofile(monkeypatch):
    def _boom(ctx):
        raise repofileutils.InvalidRepoDefinition('bad', repofile='/x.repo', repoid='x')

    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles', _boom)

    with pytest.raises(StopActorExecutionError):
        tus_targetrepos.build_target_repositories_snapshot(None)
