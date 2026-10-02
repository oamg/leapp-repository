import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import tus_constants, tus_targetrepos
from leapp.models import (
    CustomTargetRepository,
    DistroTargetRepository,
    RepositoriesFactsTarget,
    RepositoryData,
    RepositoryFile,
    RHELTargetRepository,
    TargetRepositories,
    UsedTargetRepositories,
)
from leapp.utils.deprecation import suppress_deprecation


class _Inputs(object):
    def __init__(self, target_repositories, rhui_info=None, skip_rhsm=False):
        self.target_repositories = target_repositories
        self.rhui_info = rhui_info
        self.skip_rhsm = skip_rhsm


def _repofiles(repoids):
    """Build a fake get_parsed_repofiles() result exposing repoids."""
    repos = [type('R', (), {'repoid': rid})() for rid in repoids]
    return [type('RF', (), {'data': repos})()]


@suppress_deprecation(RHELTargetRepository)
def _target_repos(distro=None, rhel=None, custom=None):
    return TargetRepositories(
        distro_repos=[DistroTargetRepository(repoid=r) for r in (distro or [])],
        rhel_repos=[RHELTargetRepository(repoid=r) for r in (rhel or [])],
        custom_repos=[CustomTargetRepository(repoid=r) for r in (custom or [])],
    )


def _patch(monkeypatch, reports, distro_repoids=None, rhui_repoids=None, available=None,
           duplicates=None, conversion=False, source_distro='rhel', source_major='9',
           target_distro='rhel'):
    monkeypatch.setattr(tus_targetrepos.distro, 'get_target_distro_repoids',
                        lambda ctx: list(distro_repoids or []))
    monkeypatch.setattr(tus_targetrepos.tus_rhui, 'discover_client_exposed_repoids',
                        lambda ctx, ri: set(rhui_repoids or []))
    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_parsed_repofiles',
                        lambda ctx: _repofiles(available or []))
    monkeypatch.setattr(tus_targetrepos.repofileutils, 'get_duplicate_repositories',
                        lambda repofiles: duplicates or {})
    monkeypatch.setattr(tus_targetrepos, 'is_conversion', lambda: conversion)
    monkeypatch.setattr(tus_targetrepos, 'get_source_distro_id', lambda: source_distro)
    monkeypatch.setattr(tus_targetrepos, 'get_source_major_version', lambda: source_major)
    monkeypatch.setattr(tus_targetrepos, 'get_target_distro_id', lambda: target_distro)
    monkeypatch.setattr(tus_targetrepos.reporting, 'create_report',
                        lambda parts: reports.append(parts))


def _titles(reports):
    out = []
    for parts in reports:
        for part in parts:
            if type(part).__name__ == 'Title':
                out.append(part.value)
    return out


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def test_requested_distro_repoids_merges_rhel_repos():
    target_repos = _target_repos(distro=['d1'], rhel=['r1'])
    assert tus_targetrepos._requested_distro_repoids(target_repos) == {'d1', 'r1'}


@pytest.mark.parametrize('repoids,expected', [
    ({'rhel-9-BaseOS', 'rhel-9-AppStream'}, True),
    ({'rhel-9-baseos'}, False),
    (set(), False),
])
def test_has_base_repos(repoids, expected):
    assert tus_targetrepos._has_base_repos(repoids) is expected


@pytest.mark.parametrize('kwargs,expected', [
    ({}, True),                                                  # default -> applies
    ({'conversion': True}, False),                              # conversions
    ({'source_distro': 'centos', 'source_major': '8'}, False),  # CS8 source
    ({'target_distro': 'rhel', 'skip_rhsm': True}, False),      # RHEL + no-rhsm
])
def test_base_repo_check_applies(monkeypatch, kwargs, expected):
    skip_rhsm = kwargs.pop('skip_rhsm', False)
    monkeypatch.setattr(tus_targetrepos, 'is_conversion', lambda: kwargs.get('conversion', False))
    monkeypatch.setattr(tus_targetrepos, 'get_source_distro_id', lambda: kwargs.get('source_distro', 'rhel'))
    monkeypatch.setattr(tus_targetrepos, 'get_source_major_version', lambda: kwargs.get('source_major', '9'))
    monkeypatch.setattr(tus_targetrepos, 'get_target_distro_id', lambda: kwargs.get('target_distro', 'rhel'))
    assert tus_targetrepos._base_repo_check_applies(skip_rhsm) is expected


# --------------------------------------------------------------------------- #
# select_target_repositories - happy path
# --------------------------------------------------------------------------- #
def test_select_happy_path(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=['baseos', 'appstream'],
           available=['baseos', 'appstream'])
    inputs = _Inputs(_target_repos(distro=['baseos', 'appstream']))

    result = tus_targetrepos.select_target_repositories(None, inputs)

    assert isinstance(result, UsedTargetRepositories)
    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos']
    assert reports == []


# --------------------------------------------------------------------------- #
# Inhibitor #2 - duplicates, only when skip_rhsm
# --------------------------------------------------------------------------- #
def test_inhibit_duplicates_when_skip_rhsm(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=['baseos', 'appstream'],
           available=['baseos', 'appstream'],
           duplicates={'baseos': {'/a.repo', '/b.repo'}})
    inputs = _Inputs(_target_repos(distro=['baseos', 'appstream']), skip_rhsm=True)

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'A duplicate repository definition was found' in _titles(reports)


def test_no_duplicate_check_without_skip_rhsm(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=['baseos', 'appstream'],
           available=['baseos', 'appstream'],
           duplicates={'baseos': {'/a.repo', '/b.repo'}})
    inputs = _Inputs(_target_repos(distro=['baseos', 'appstream']), skip_rhsm=False)

    # duplicates present but RHSM active -> not inspected, no inhibitor
    result = tus_targetrepos.select_target_repositories(None, inputs)
    assert sorted(r.repoid for r in result.repos) == ['appstream', 'baseos']
    assert reports == []


# --------------------------------------------------------------------------- #
# Inhibitor #3 - missing base repos + skip conditions
# --------------------------------------------------------------------------- #
def test_inhibit_missing_base_repos(monkeypatch):
    reports = []
    _patch(monkeypatch, reports, distro_repoids=['foo'], available=['foo'])
    inputs = _Inputs(_target_repos(distro=['foo']))

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'Cannot find required basic RHEL target repositories' in _titles(reports)


def test_base_repo_check_skipped_for_conversion(monkeypatch):
    reports = []
    _patch(monkeypatch, reports, distro_repoids=['foo'], available=['foo'], conversion=True)
    inputs = _Inputs(_target_repos(distro=['foo']))

    # No base repos, but conversion -> #3 skipped; selection non-empty -> ok.
    result = tus_targetrepos.select_target_repositories(None, inputs)
    assert [r.repoid for r in result.repos] == ['foo']
    assert reports == []


# --------------------------------------------------------------------------- #
# Inhibitor #4 - no enabled target repos
# --------------------------------------------------------------------------- #
def test_inhibit_no_enabled_repos(monkeypatch):
    reports = []
    # skip_rhsm + target rhel -> base check does not apply; nothing discovered.
    _patch(monkeypatch, reports, distro_repoids=[], available=[])
    inputs = _Inputs(_target_repos(distro=['foo']), skip_rhsm=True)

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'There are no enabled target repositories' in _titles(reports)


# --------------------------------------------------------------------------- #
# Inhibitor #5 - missing custom repos
# --------------------------------------------------------------------------- #
def test_inhibit_missing_custom_repos(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=['baseos', 'appstream'],
           available=['baseos', 'appstream'])   # custom1 not available
    inputs = _Inputs(_target_repos(distro=['baseos', 'appstream'], custom=['custom1']))

    with pytest.raises(StopActorExecution):
        tus_targetrepos.select_target_repositories(None, inputs)

    assert 'Some required repositories are not available' in _titles(reports)


# --------------------------------------------------------------------------- #
# RHUI-discovered repoids feed the selection
# --------------------------------------------------------------------------- #
def test_rhui_repoids_included_in_selection(monkeypatch):
    reports = []
    _patch(monkeypatch, reports,
           distro_repoids=[],
           rhui_repoids=['rhui-baseos', 'rhui-appstream'],
           available=['rhui-baseos', 'rhui-appstream'])
    inputs = _Inputs(_target_repos(distro=['rhui-baseos', 'rhui-appstream']), rhui_info=object())

    result = tus_targetrepos.select_target_repositories(None, inputs)
    assert sorted(r.repoid for r in result.repos) == ['rhui-appstream', 'rhui-baseos']


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
