from functools import partial

import pytest

from leapp.libraries.actor import pes_events_scanner
from leapp.libraries.actor.pes_event_parsing import Event
from leapp.libraries.actor.pes_events_scanner import (
    Action,
    api,
    compute_packages_on_target_system,
    compute_rpm_tasks_from_pkg_set_diff,
    get_installed_pkgs,
    Package,
    process,
    reporting,
    TransactionConfiguration
)
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.models import (
    EnabledModules,
    InstalledRedHatSignedRPM,
    PESIDRepositoryEntry,
    PESRpmTransactionTasks,
    RepoMapEntry,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RepositoryData,
    RepositoryFile,
    RHUIInfo,
    RPM
)


def pkgs_into_tuples(pkgs):
    return {(p.name, p.repository, p.modulestream) for p in pkgs}


@pytest.mark.parametrize(
    ('installed_pkgs', 'events', 'releases', 'expected_target_pkgs'),
    (
        (
            {Package('original', 'rhel7-repo', None)},
            [
                Event(1, Action.SPLIT, {Package('original', 'rhel7-repo', None)},
                      {Package('split01', 'rhel8-repo', None), Package('split02', 'rhel8-repo', None)},
                      (7, 6), (8, 0), [])
            ],
            [(8, 0)],
            {Package('split01', 'rhel8-repo', None), Package('split02', 'rhel8-repo', None), }
        ),
        (
            {Package('removed', 'rhel7-repo', None)},
            [Event(1, Action.REMOVED, {Package('removed', 'rhel7-repo', None)}, set(), (7, 6), (8, 0), [])],
            [(8, 0)],
            set()
        ),
        (
            {Package('present', 'rhel7-repo', None)},
            [Event(1, Action.PRESENT, {Package('present', 'rhel8-repo', None)}, set(), (7, 6), (8, 0), [])],
            [(8, 0)],
            {Package('present', 'rhel8-repo', None)}
        ),
        (
            {Package('reintroduced', 'rhel7-repo', None)},
            [
                Event(1, Action.REMOVED, {Package('reintroduced', 'rhel8-repo', None)}, set(), (7, 6), (8, 0), []),
                Event(2, Action.PRESENT, {Package('reintroduced', 'rhel8-repo', None)}, set(), (8, 0), (8, 1), []),
            ],
            [(8, 0), (8, 1)],
            {Package('reintroduced', 'rhel8-repo', None)}
        ),
        (
            {Package('merge-in1', 'rhel7-repo', None), Package('merge-in2', 'rhel7-repo', None)},
            [
                Event(1, Action.MERGED,
                      {Package('merge-in1', 'rhel7-repo', None), Package('merge-in2', 'rhel7-repo', None)},
                      {Package('merge-out', 'rhel8-repo', None)}, (7, 6), (8, 0), []),
            ],
            [(8, 0)],
            {Package('merge-out', 'rhel8-repo', None)}
        ),
        (
            {Package('merge-in1', 'rhel7-repo', None)},
            [
                Event(1, Action.MERGED,
                      {Package('merge-in1', 'rhel7-repo', None), Package('merge-in2', 'rhel7-repo', None)},
                      {Package('merge-out', 'rhel8-repo', None)}, (7, 6), (8, 0), []),
            ],
            [(8, 0)],
            {Package('merge-out', 'rhel8-repo', None)}
        ),
        (
            {Package('deprecated', 'rhel7-repo', None)},
            [Event(1, Action.DEPRECATED, {Package('deprecated', 'rhel8-repo', None)}, set(), (7, 6), (8, 0), [])],
            [(8, 0)],
            {Package('deprecated', 'rhel8-repo', None)}
        ),
        (
            {Package('replaced-in', 'rhel7-repo', None)},
            [
                Event(1, Action.REPLACED, {Package('replaced-in', 'rhel7-repo', None)},
                      {Package('replaced-out', 'rhel8-repo', None)}, (7, 6), (8, 0), [])
            ],
            [(8, 0)],
            {Package('replaced-out', 'rhel8-repo', None)}
        ),
        (
            {Package('moved-in', 'rhel7-repo', None)},
            [
                Event(1, Action.MOVED, {Package('moved-in', 'rhel7-repo', None)},
                      {Package('moved-out', 'rhel8-repo', None)}, (7, 6), (8, 0), [])
            ],
            [(8, 0)],
            {Package('moved-out', 'rhel8-repo', None)}
        ),
        (
            {Package('renamed-in', 'rhel7-repo', None)},
            [
                Event(1, Action.RENAMED, {Package('renamed-in', 'rhel7-repo', None)},
                      {Package('renamed-out', 'rhel8-repo', None)}, (7, 6), (8, 0), [])
            ],
            [(8, 0)],
            {Package('renamed-out', 'rhel8-repo', None)}
        ),
    )
)
def test_event_application_fundamentals(monkeypatch, installed_pkgs, events, releases, expected_target_pkgs):
    """Trivial checks validating that the core event application algorithm reflects event semantics as expected."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    actual_target_pkgs, dummy_demodularized_pkgs = compute_packages_on_target_system(installed_pkgs, events, releases)

    # Perform strict comparison
    actual_pkg_tuple_set = {(pkg.name, pkg.repository, pkg.modulestream) for pkg in actual_target_pkgs}
    expected_pkg_tuple_set = {(pkg.name, pkg.repository, pkg.modulestream) for pkg in expected_target_pkgs}
    assert actual_pkg_tuple_set == expected_pkg_tuple_set


def test_compute_pkg_state(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    events = [
        Event(1, Action.SPLIT,
              {Package('original', 'rhel7-repo', None)},
              {Package('split01', 'rhel8-repo', None), Package('split02', 'rhel8-repo', None)},
              (7, 6), (8, 0), []),
        Event(2, Action.REMOVED,
              {Package('removed', 'rhel7-repo', None)}, set(),
              (7, 6), (8, 0), []),
        Event(3, Action.PRESENT,
              {Package('present', 'rhel8-repo', None)}, set(),
              (7, 6), (8, 0), []),
        Event(4, Action.REMOVED,
              {Package('reintroduced', 'rhel7-repo', None)}, set(),
              (7, 6), (8, 0), []),
        Event(5, Action.PRESENT,
              {Package('reintroduced', 'rhel8-repo', None)}, set(),
              (8, 0), (8, 1), []),
        Event(6, Action.PRESENT,
              set(), {Package('neverthere', 'rhel8-repo', None)},
              (8, 0), (8, 1), [])
    ]

    installed_pkgs = {
        Package('original', 'rhel7-repo', None),
        Package('removed', 'rhel7-repo', None),
        Package('present', 'rhel7-repo', None),
        Package('reintroduced', 'rhel7-repo', None),
    }

    target_pkgs, dummy_demodularized_pkgs = compute_packages_on_target_system(installed_pkgs, events, [(8, 0), (8, 1)])

    expected_target_pkgs = {
        Package('split01', 'rhel8-repo', None),
        Package('split02', 'rhel8-repo', None),
        Package('present', 'rhel8-repo', None),
        Package('reintroduced', 'rhel8-repo', None),
    }
    assert target_pkgs == expected_target_pkgs


def test_compute_rpm_tasks_from_pkg_set_diff(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[EnabledModules(modules=[])]))
    source_pkgs = {
        Package('removed1', '7repo', None),
        Package('removed2', '7repo', None),
        Package('kept1', '7repo', None),
        Package('kept2', '7repo', None),
    }

    target_pkgs = {
        Package('kept1', '8repo0', None),
        Package('kept2', '8repo0', None),
        Package('installed1', '8repo1', None),
        Package('installed2', '8repo2', None),
    }

    rpm_tasks = compute_rpm_tasks_from_pkg_set_diff(source_pkgs, target_pkgs, set())

    assert rpm_tasks.to_install == ['installed1', 'installed2']
    assert rpm_tasks.to_remove == ['removed1', 'removed2']


def test_actor_performs(monkeypatch):
    """Test whether the actor performs as expected when supplied with required messages."""

    Pkg = partial(Package, modulestream=None)

    events = [
        Event(1, Action.SPLIT,
              {Pkg('split-in', 'rhel7-base')},
              {Pkg('split-out0', 'rhel8-BaseOS'), Pkg('split-out1', 'rhel8-BaseOS')},
              (7, 9), (8, 0), []),
        Event(2, Action.MERGED,
              {Pkg('split-out0', 'rhel8-BaseOS'), Pkg('split-out1', 'rhel8-BaseOS')},
              {Pkg('merged-out', 'rhel8-BaseOS')},
              (8, 0), (8, 1), []),
        Event(3, Action.MOVED,
              {Pkg('moved-in', 'rhel7-base')}, {Pkg('moved-out', 'rhel8-BaseOS')},
              (7, 9), (8, 0), []),
        Event(4, Action.REMOVED,
              {Pkg('removed', 'rhel7-base')}, set(),
              (8, 0), (8, 1), []),
        Event(5, Action.DEPRECATED,
              {Pkg('irrelevant', 'rhel7-base')}, set(),
              (8, 0), (8, 1), []),
    ]

    monkeypatch.setattr(pes_events_scanner, 'get_pes_events', lambda data_folder, json_filename: events)

    _RPM = partial(RPM, epoch='', packager='', version='', release='', arch='', pgpsig='')

    installed_pkgs = InstalledRedHatSignedRPM(items=[
        _RPM(name='split-in'), _RPM(name='moved-in'), _RPM(name='removed')
    ])

    repositories_mapping = RepositoriesMapping(
        mapping=[
            RepoMapEntry(source='rhel7-base', target=['rhel8-BaseOS'], ),
        ],
        repositories=[
            PESIDRepositoryEntry(pesid='rhel7-base', major_version='7', repoid='rhel7-repo', arch='x86_64',
                                 repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-repo', arch='x86_64',
                                 repo_type='rpm', channel='ga', rhui='')]
    )

    enabled_modules = EnabledModules(modules=[])
    repo_facts = RepositoriesFacts(
        repositories=[RepositoryFile(file='', data=[RepositoryData(repoid='rhel7-repo', name='RHEL7 repo')])]
    )

    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(msgs=[installed_pkgs, repositories_mapping, enabled_modules, repo_facts],
                                           src_ver='7.9', dst_ver='8.1'))

    produced_messages = produce_mocked()
    created_report = create_report_mocked()
    monkeypatch.setattr(api, 'produce', produced_messages)
    monkeypatch.setattr(reporting, 'create_report', created_report)

    pes_events_scanner.process()

    assert produced_messages.called

    produced_rpm_tasks = [msg for msg in produced_messages.model_instances if isinstance(msg, PESRpmTransactionTasks)]
    expected_rpm_tasks = PESRpmTransactionTasks(to_install=['merged-out', 'moved-out'],
                                                to_remove=['moved-in', 'removed', 'split-in'],
                                                modules_to_enable=[],
                                                modules_to_reset=[])
    assert len(produced_rpm_tasks) == 1
    assert produced_rpm_tasks[0].to_install == expected_rpm_tasks.to_install
    assert produced_rpm_tasks[0].to_remove == expected_rpm_tasks.to_remove
    assert produced_rpm_tasks[0].modules_to_enable == expected_rpm_tasks.modules_to_enable
    assert produced_rpm_tasks[0].modules_to_reset == expected_rpm_tasks.modules_to_reset


def test_transaction_configuration_has_effect(monkeypatch):
    _Pkg = partial(Package, repository=None, modulestream=None)

    def mocked_transaction_conf():
        return TransactionConfiguration(
            to_install=[_Pkg('pkg-a'), _Pkg('pkg-b')],
            to_remove=[_Pkg('pkg-c'), _Pkg('pkg-d')],
            to_keep=[]
        )

    monkeypatch.setattr(pes_events_scanner, 'get_transaction_configuration', mocked_transaction_conf)

    packages = {_Pkg('pkg-a'), _Pkg('pkg-c')}
    _result = pes_events_scanner.apply_transaction_configuration(packages)
    result = {(p.name, p.repository, p.modulestream) for p in _result}
    expected = {('pkg-a', None, None), ('pkg-b', None, None)}

    assert result == expected


def test_repository_blacklist_is_correctly_applied(monkeypatch):
    _Pkg = partial(Package, modulestream=None)

    monkeypatch.setattr(pes_events_scanner, 'get_blacklisted_repoids', lambda: {'repo-a', 'repo-b', 'repo-c'})
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    source_pkgs = {_Pkg('pkg-b', 'repo-b')}
    target_pkgs = {_Pkg('pkg-a', 'repo-a'), _Pkg('pkg-b', 'repo-b'), _Pkg('pkg-c', 'repo-c'), _Pkg('pkg-d', 'repo-d')}

    blacklisted_repoids, target_pkgs = pes_events_scanner.remove_new_packages_from_blacklisted_repos(source_pkgs,
                                                                                                     target_pkgs)
    result = pkgs_into_tuples(target_pkgs)

    assert blacklisted_repoids == {'repo-a', 'repo-b', 'repo-c'}
    assert result == {('pkg-b', 'repo-b', None), ('pkg-d', 'repo-d', None)}

    assert reporting.create_report.called
    for removed_pkg_name in ('pkg-a', 'pkg-c'):
        assert removed_pkg_name in reporting.create_report.reports[0]['summary']


def test_blacklisted_repoid_is_not_produced(monkeypatch):
    """
    Test that upgrade with a package that would be from a blacklisted repository on the target system does not remove
    the package as it was already installed, however, the blacklisted repoid should not be produced.
    """
    installed_pkgs = {Package('pkg-a', 'blacklisted-rhel7', None), Package('pkg-b', 'repoid-rhel7', None)}
    events = [
        Event(1, Action.MOVED, {Package('pkg-b', 'repoid-rhel7', None)}, {Package('pkg-b', 'repoid-rhel8', None)},
              (8, 0), (8, 1), []),
        Event(2, Action.MOVED, {Package('pkg-a', 'repoid-rhel7', None)}, {Package('pkg-a', 'blacklisted-rhel8', None)},
              (8, 0), (8, 1), []),
    ]

    monkeypatch.setattr(pes_events_scanner, 'get_installed_pkgs', lambda: installed_pkgs)
    monkeypatch.setattr(pes_events_scanner, 'get_pes_events', lambda folder, filename: events)
    monkeypatch.setattr(pes_events_scanner, 'apply_transaction_configuration', lambda pkgs: pkgs)
    monkeypatch.setattr(pes_events_scanner, 'get_blacklisted_repoids', lambda: {'blacklisted-rhel8'})
    monkeypatch.setattr(pes_events_scanner, 'replace_pesids_with_repoids_in_packages',
                        lambda pkgs, src_pkgs_repoids: pkgs)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    pes_events_scanner.process()

    assert not reporting.create_report.called

    rpm_tasks = [msg for msg in api.produce.model_instances if isinstance(msg, PESRpmTransactionTasks)]

    fail_desc = ('pkg-a should not be removed as it is already installed, and it just won\'t be upgraded since its '
                 'repository is blacklisted. All remaining pkgs are kept, no new pkgs are installed, and therefore, '
                 'no PESRpmTransactionTasks should be produced, however, they were.')
    assert not rpm_tasks, fail_desc

    repo_setup_tasks = [msg for msg in api.produce.model_instances if isinstance(msg, RepositoriesSetupTasks)]
    assert len(repo_setup_tasks) == 1
    assert repo_setup_tasks[0].to_enable == ['repoid-rhel8']


@pytest.mark.parametrize(
    ('installed_pkgs', 'expected_target_pkgs'),
    (
        ({Package('in', 'rhel7-repo', ('m', 's'))}, {('out', 'rhel8-repo-modular', ('m', 's'))}),
        ({Package('in', 'rhel7-repo', None)}, {('out', 'rhel8-repo', None)}),
    )
)
def test_modularity_info_distinguishes_pkgs(monkeypatch, installed_pkgs, expected_target_pkgs):
    events = [
        Event(1, Action.MOVED,
              {Package('in', 'rhel7-repo', None)}, {Package('out', 'rhel8-repo', None)},
              (8, 0), (8, 1), []),
        Event(2, Action.MOVED,
              {Package('in', 'rhel7-repo', ('m', 's'))}, {Package('out', 'rhel8-repo-modular', ('m', 's'))},
              (8, 0), (8, 1), []),
    ]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    target_pkgs, dummy_demodularized_pkgs = compute_packages_on_target_system(installed_pkgs, events, [(8, 1)])

    assert pkgs_into_tuples(target_pkgs) == expected_target_pkgs


def test_pkgs_are_demodularized_when_crossing_major_version(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='7.9'))

    events = [
        Event(1, Action.MOVED,
              {Package('modular', 'repo1-in', ('module1', 'stream'))},
              {Package('modular', 'repo1-out', ('module2', 'stream'))},
              (7, 9), (8, 0), []),
    ]

    installed_pkgs = {
        Package('modular', 'repo1-in', ('module1', 'stream')),
        Package('demodularized', 'repo', ('module-demodularized', 'stream'))
    }

    target_pkgs, demodularized_pkgs = compute_packages_on_target_system(installed_pkgs, events, [(8, 0)])

    expected_target_pkgs = {
        Package('modular', 'repo1-out', ('module2', 'stream')),
        Package('demodularized', 'repo', None)
    }
    assert demodularized_pkgs == {Package('demodularized', 'repo', ('module-demodularized', 'stream'))}
    assert target_pkgs == expected_target_pkgs
