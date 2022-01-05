import functools
import os.path
from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import peseventsscanner
from leapp.libraries.actor.peseventsscanner import (
    Action,
    add_output_pkgs_to_transaction_conf,
    drop_conflicting_release_events,
    Event,
    filter_events_by_architecture,
    filter_events_by_releases,
    filter_irrelevant_releases,
    filter_out_pkgs_in_blacklisted_repos,
    get_events,
    map_repositories,
    Package,
    parse_action,
    parse_entry,
    parse_packageset,
    parse_pes_events,
    process_events,
    report_skipped_packages,
    SKIPPED_PKGS_MSG,
    Task
)
from leapp.libraries.common import fetch
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RepoMapEntry, RepositoriesMapping, RpmTransactionTasks

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class show_message_mocked(object):
    def __init__(self):
        self.called = 0
        self.msg = None

    def __call__(self, msg):
        self.called += 1
        self.msg = msg


class get_repos_blacklisted_mocked(object):
    def __init__(self, blacklisted):
        self.blacklisted = blacklisted

    def __call__(self):
        return self.blacklisted


def test_parse_action(current_actor_context):
    for i in range(8):
        assert parse_action(i) == Action(i)

    with pytest.raises(ValueError):
        parse_action(-1)
        parse_action(8)


def test_parse_packageset(current_actor_context):
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo'}]}

    parsed = parse_packageset(pkgset)
    assert len(parsed) == 1
    assert Package('pkg1', 'Repo', (None,)) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


def test_parse_packageset_modular(current_actor_context):
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo', 'modulestreams': [None]},
                          {'name': 'pkg2', 'repository': 'Repo', 'modulestreams': [{
                              'name': 'hey', 'stream': 'lol'
                          }]}]}

    parsed = parse_packageset(pkgset)
    assert len(parsed) == 2
    assert Package('pkg1', 'Repo', (None,)) in parsed
    assert Package('pkg2', 'Repo', (('hey', 'lol'),)) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


def test_parse_entry(current_actor_context):
    """
    Tests whether the PES event is correctly parsed from the supplied dictionary with the same
    structure as are the data stored inside the json.
    """
    entry = {
        'action': 4,
        'in_packageset': {
            'package': [{'name': 'original', 'repository': 'repo'}]},
        'out_packageset': {
            'package': [
                {'name': 'split01', 'repository': 'repo'},
                {'name': 'split02', 'repository': 'repo'}]}}

    events = parse_entry(entry)
    assert len(events) == 1
    event = events.pop()
    assert event.action == Action.SPLIT
    assert event.in_pkgs == {Package('original', 'repo', None)}
    assert event.out_pkgs == {Package('split01', 'repo', None), Package('split02', 'repo', None)}

    entry = {
        'action': 1,
        'in_packageset': {
            'package': [{'name': 'removed', 'repository': 'repo'}]}}

    events = parse_entry(entry)
    assert len(events) == 1
    event = events.pop()
    assert event.action == Action.REMOVED
    assert event.in_pkgs == {Package('removed', 'repo', None)}
    assert event.out_pkgs == set()


def test_parse_pes_events(current_actor_context):
    """
    Tests whether all events are correctly parsed from the provided string with the JSON data.
    """
    with open(os.path.join(CUR_DIR, 'files/sample01.json')) as f:
        events = parse_pes_events(f.read())
    assert len(events) == 2
    assert events[0].action == Action.SPLIT
    assert events[0].in_pkgs == {Package('original', 'repo', None)}
    assert events[0].out_pkgs == {Package('split01', 'repo', None), Package('split02', 'repo', None)}
    assert events[1].action == Action.REMOVED
    assert events[1].in_pkgs == {Package('removed', 'repo', None)}
    assert events[1].out_pkgs == set()


def test_parse_pes_events_with_modulestreams(current_actor_context):
    """
    Tests whether all events are correctly parsed from the provided string with the JSON data.
    """
    with open(os.path.join(CUR_DIR, 'files/sample04.json')) as f:
        events = parse_pes_events(f.read())
    assert len(events) == 5
    Expected = namedtuple('Expected', 'action,in_pkgs,out_pkgs')
    expected = [
        Expected(action=Action.SPLIT, in_pkgs={Package('original', 'repo', ('module', 'stream_in'))}, out_pkgs={
                 Package('split01', 'repo', None), Package('split02', 'repo', None)}),
        Expected(action=Action.SPLIT, in_pkgs={Package('original', 'repo', None)},
                 out_pkgs={Package('split01', 'repo', ('module', 'stream_out')),
                           Package('split02', 'repo', ('module', 'stream_out'))}),
        Expected(action=Action.REMOVED, in_pkgs={Package('removed', 'repo', None)}, out_pkgs=set()),
        Expected(action=Action.RENAMED, in_pkgs={Package('modularized', 'repo', ('module', 'stream_in'))}, out_pkgs={
                 Package('demodularized', 'repo', None)}),
        Expected(action=Action.RENAMED, in_pkgs={Package('modularized', 'repo', None)}, out_pkgs={
                 Package('demodularized', 'repo', None)}),
    ]

    for event in events:
        for idx, expectation in enumerate(list(expected)):
            if expectation.action == event.action and expectation.in_pkgs == event.in_pkgs:
                assert event.out_pkgs == expectation.out_pkgs
                expected.pop(idx)
                break
        if not expected:
            break
    assert not expected


@ pytest.mark.parametrize('is_verbose_mode_on', [False, True])
def test_report_skipped_packages_no_verbose_mode(monkeypatch, caplog, is_verbose_mode_on):
    """
    Tests whether the report_skipped_packages function creates message of the expected form
    and that the function respects whether leapp is running in verbose mode.
    """
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    report_skipped_packages(
        title='Packages will not be installed',
        message='packages will not be installed:',
        package_repo_pairs=[(('skipped01', None), 'bad_repo01'), (('skipped02', ('module', 'stream')), 'bad_repo02')]
    )

    message = (
        '2 packages will not be installed:\n'
        '- skipped01 (repoid: bad_repo01)\n'
        '- skipped02 [module:stream] (repoid: bad_repo02)'
    )
    assert message in caplog.messages
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'Packages will not be installed'
    assert reporting.create_report.report_fields['summary'] == message

    leapp_verbose = '1' if is_verbose_mode_on else '0'

    monkeypatch.setenv('LEAPP_VERBOSE', leapp_verbose)
    # Reset reporting.create_report for next test part
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    report_skipped_packages(
        title='Packages will not be installed',
        message='packages will not be installed:',
        package_repo_pairs=[(('skipped01', None), 'bad_repo01'), (('skipped02', ('module', 'stream')), 'bad_repo02')]
    )

    # FIXME(pstodulk): this is obviously wrong. repoid is currently pesid.. so test
    # is incorrect, and code is incorrect. even the message is missleading.
    # this is going to be fixed in close future.
    message = (
        '2 packages will not be installed:\n'
        '- skipped01 (repoid: bad_repo01)\n'
        '- skipped02 [module:stream] (repoid: bad_repo02)'
    )

    # Verbose level should only control whether show_message is called, report entry should be created
    # in both cases.
    if is_verbose_mode_on:
        assert message in caplog.messages
    else:
        assert api.show_message.called == 0

    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'Packages will not be installed'
    assert reporting.create_report.report_fields['summary'] == message


def test_filter_out_pkgs_in_blacklisted_repos(monkeypatch, caplog):
    """
    Verifies that packages from blacklisted repos are filtered out.

    Verifies that the dictionary mapping packages to the target repoids gets correctly cleansed of all entries
    containing a blacklisted target repository when using filter_out_pkgs_in_blacklisted_repos. Also verifies
    that the user gets informed about packages not being installed due to a blacklisted repository.
    """
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(peseventsscanner, 'get_repositories_blacklisted',
                        get_repos_blacklisted_mocked(set(['blacklisted'])))
    monkeypatch.setenv('LEAPP_VERBOSE', '1')

    to_install = {
        ('pkg01', None): 'repo01',
        ('pkg02', ('module', 'stream')): 'repo02',
        ('skipped01', None): 'blacklisted',
        ('skipped02', ('module', 'stream')): 'blacklisted',
    }

    pkgs_with_blacklisted_repo = sorted((pkg, repo) for pkg, repo in to_install.items() if repo == 'blacklisted')

    msg = '2 {}\n{}'.format(
        SKIPPED_PKGS_MSG,
        '\n'.join(
            [
                '- {pkg}{ms} (repoid: {repo})'.format(pkg=pkg[0], repo=repo,
                                                      ms=(' [{}:{}]'.format(*pkg[1]) if pkg[1] else ''))
                for pkg, repo in pkgs_with_blacklisted_repo
            ]
        )
    )

    filter_out_pkgs_in_blacklisted_repos(to_install)

    assert msg in caplog.messages
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['summary'] == msg
    assert reporting.create_report.report_fields['title'] == (
        'Packages available in excluded repositories will not be installed'
    )

    assert to_install == {('pkg01', None): 'repo01', ('pkg02', ('module', 'stream')): 'repo02'}


def test_resolve_conflicting_requests(monkeypatch):
    """
    Verifies that the algorithm correctly resolves conflicting pes events.
    """
    monkeypatch.setattr(peseventsscanner, 'map_repositories', lambda x: x)
    monkeypatch.setattr(peseventsscanner, 'filter_out_pkgs_in_blacklisted_repos', lambda x: x)

    events = [
        Event(1, Action.SPLIT,
              {Package('sip-devel', 'repo', None)},
              {Package('python3-sip-devel', 'repo', None), Package('sip', 'repo', None)},
              (7, 6), (8, 0), []),
        Event(2, Action.SPLIT,
              {Package('sip', 'repo', None)},
              {Package('python3-pyqt5-sip', 'repo', None), Package('python3-sip', 'repo', None)},
              (7, 6), (8, 0), [])]
    installed_pkgs = {('sip', None), ('sip-devel', None)}

    tasks = process_events([(8, 0)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {('python3-sip-devel', None): 'repo',
                                   ('python3-pyqt5-sip', None): 'repo',
                                   ('python3-sip', None): 'repo'}
    assert tasks[Task.REMOVE] == {('sip-devel', None): 'repo'}
    assert tasks[Task.KEEP] == {('sip', None): 'repo'}


@ pytest.mark.parametrize(('source_repoid', 'expected_target_repoid'),
                          [('rhel7-base-repoid', 'rhel8-crb-repoid'),
                          ('rhel7-base-repoid-eus', 'rhel8-crb-repoid-eus')])
def test_request_pesid_repo_not_mapped_by_default(monkeypatch, source_repoid, expected_target_repoid):
    """
    Tests whether a target repository that is not mapped by default (e.g. CRB)
    is requested to be enabled on the target system if it results from the relevant events.

    Note: Since the resulting target repository is not mapped by default from the enabled repositories,
          the data handler should fail to get expected repoids for the given pesid as it works with enabled
          repositories. Therefor, this test tests whether the fallback lookup with representative repository works.
    """

    repositories_mapping = RepositoriesMapping(
        mapping=[
            RepoMapEntry(source='rhel7-base', target=['rhel8-BaseOS', 'rhel8-AppStream']),
            RepoMapEntry(source='rhel7-optional', target=['rhel8-CRB']),
        ],
        repositories=[
            PESIDRepositoryEntry(pesid='rhel7-base', major_version='7', repoid='rhel7-base-repoid',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel7-base', major_version='7', repoid='rhel7-base-repoid-eus',
                                 arch='x86_64', repo_type='rpm', channel='eus', rhui=''),
            PESIDRepositoryEntry(pesid='rhel7-optional', major_version='7', repoid='rhel7-optional-repoid',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-baseos-repoid',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-baseos-repoid-eus',
                                 arch='x86_64', repo_type='rpm', channel='eus', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-AppStream', major_version='8', repoid='rhel8-appstream-repoid',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-CRB', major_version='8', repoid='rhel8-crb-repoid',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-CRB', major_version='8', repoid='rhel8-crb-repoid-eus',
                                 arch='x86_64', repo_type='rpm', channel='eus', rhui=''),
        ])

    monkeypatch.setattr(peseventsscanner, '_get_enabled_repoids', lambda: {source_repoid})
    monkeypatch.setattr(api,
                        'current_actor',
                        CurrentActorMocked(msgs=[repositories_mapping], src_ver='7.9', dst_ver='8.4'))

    event = Event(1, Action.MOVED, {Package('test-pkg', 'rhel7-base', None)}, {Package('test-pkg', 'rhel8-CRB', None)},
                  (7, 9), (8, 0), [])
    installed_pkgs = {('test-pkg', None)}

    tasks = process_events([(8, 0)], [event], installed_pkgs)

    assert tasks[Task.KEEP] == {('test-pkg', None): expected_target_repoid}


def test_get_repositories_mapping(monkeypatch):
    """
    Tests whether the actor is able to correctly determine the dictionary that maps the target PES ids
    determined from the event processing to the actual target repository ids.
    (tests for the _get_repositories_mapping).
    """

    make_pesid_repo = functools.partial(PESIDRepositoryEntry, arch='x86_64', repo_type='rpm', channel='ga', rhui='')
    repositories_mapping = RepositoriesMapping(
        mapping=[
            RepoMapEntry(source='rhel7-base', target=['rhel8-BaseOS', 'rhel8-AppStream']),
            RepoMapEntry(source='rhel7-optional', target=['rhel8-CRB']),
        ],
        repositories=[
            make_pesid_repo(pesid='rhel7-base', major_version='7', repoid='rhel7-base-repoid'),
            make_pesid_repo(pesid='rhel7-optional', major_version='7', repoid='rhel7-optional-repoid'),
            make_pesid_repo(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-baseos-repoid'),
            make_pesid_repo(pesid='rhel8-AppStream', major_version='8', repoid='rhel8-appstream-repoid'),
            make_pesid_repo(pesid='rhel8-CRB', major_version='8', repoid='rhel8-crb-repoid'),
            # Extra repositories to make sure the created map contains the correct repoids
            PESIDRepositoryEntry(pesid='rhel8-CRB', major_version='8', repoid='rhel8-crb-repoid-azure',
                                 arch='x86_64', repo_type='rpm', channel='ga', rhui='azure'),
            PESIDRepositoryEntry(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-baseos-repoid-eus',
                                 arch='x86_64', repo_type='rpm', channel='eus', rhui=''),
            PESIDRepositoryEntry(pesid='rhel8-BaseOS', major_version='8', repoid='rhel8-baseos-repoid-s390x',
                                 arch='s390x', repo_type='rpm', channel='ga', rhui=''),
        ])

    monkeypatch.setattr(peseventsscanner, '_get_enabled_repoids', lambda: {'rhel7-base-repoid'})
    monkeypatch.setattr(api,
                        'current_actor',
                        CurrentActorMocked(msgs=[repositories_mapping], src_ver='7.9', dst_ver='8.4'))

    target_pesids = {'rhel8-BaseOS', 'rhel8-AppStream', 'rhel8-CRB'}
    expected_pesid_to_target_repoids = {
        'rhel8-BaseOS': 'rhel8-baseos-repoid',
        'rhel8-AppStream': 'rhel8-appstream-repoid',
        'rhel8-CRB': 'rhel8-crb-repoid'
    }

    actual_pesid_to_target_repoids = peseventsscanner._get_repositories_mapping(target_pesids)

    fail_description = 'Actor failed to determine what repoid to enable for given target pesids.'
    assert actual_pesid_to_target_repoids == expected_pesid_to_target_repoids, fail_description


def test_pesid_to_target_repoids_translation(monkeypatch, caplog):
    """
    Tests whether the actor is able to correctly translate target pesids resulting
    from event processing when it is supplied with a valid dictionary that maps pesids to target repoids.
    """
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(peseventsscanner, '_get_repositories_mapping', lambda dummy_target_pesids: {'repo': 'mapped'})
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '1')

    to_install = {
        ('pkg01', None): 'repo',
        ('pkg02', ('module', 'stream')): 'repo',
        ('skipped01', None): 'not_mapped',
        ('skipped02', ('module', 'stream')): 'not_mapped'}
    map_repositories(to_install)

    msg = (
        '2 packages may not be installed or upgraded due to repositories unknown to leapp:\n'
        '- skipped01 (repoid: not_mapped)\n'
        '- skipped02 [module:stream] (repoid: not_mapped)'
    )
    assert msg in caplog.messages
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == (
        'Packages from unknown repositories may not be installed'
    )
    assert reporting.create_report.report_fields['summary'] == msg

    assert to_install == {('pkg01', None): 'mapped', ('pkg02', ('module', 'stream')): 'mapped'}


def test_process_events(monkeypatch):
    """
    Verifies that the event processing algorithm works as expected.
    """
    monkeypatch.setattr(peseventsscanner,
                        '_get_repositories_mapping',
                        lambda dummy_target_pesids: {'rhel8-repo': 'rhel8-mapped'})
    monkeypatch.setattr(peseventsscanner, 'get_repositories_blacklisted', get_repos_blacklisted_mocked(set()))

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
        # this package is present at the start, gets removed and then reintroduced
        Event(4, Action.REMOVED,
              {Package('reintroduced', 'rhel7-repo', None)}, set(),
              (7, 6), (8, 0), []),
        Event(5, Action.PRESENT,
              {Package('reintroduced', 'rhel8-repo', None)}, set(),
              (8, 0), (8, 1), []),
        # however, this package was never there
        Event(6, Action.REMOVED,
              {Package('neverthere', 'rhel7-repo', None)}, set(),
              (7, 6), (8, 0), []),
        Event(7, Action.PRESENT,
              {Package('neverthere', 'rhel8-repo', None)}, set(),
              (8, 0), (8, 1), [])]
    installed_pkgs = {('original', None), ('removed', None), ('present', None), ('reintroduced', None)}
    tasks = process_events([(8, 0), (8, 1)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {('split02', None): 'rhel8-mapped', ('split01', None): 'rhel8-mapped'}
    assert tasks[Task.REMOVE] == {('removed', None): 'rhel7-repo', ('original', None): 'rhel7-repo'}
    assert tasks[Task.KEEP] == {('present', None): 'rhel8-mapped', ('reintroduced', None): 'rhel8-mapped'}


def test_get_events(monkeypatch):
    """
    Verifies that the actor gracefully handles errors raised when unable to load events from a file
    and inhibits the upgrade in such case.
    """
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    with pytest.raises(StopActorExecution):
        get_events(os.path.join(CUR_DIR, 'files'), 'sample02.json')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']

    reporting.create_report.called = 0
    reporting.create_report.model_instances = []
    with pytest.raises(StopActorExecution):
        get_events(os.path.join(CUR_DIR, 'files'), 'sample03.json')
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']


def test_pes_data_not_found(monkeypatch):
    def read_or_fetch_mocked(filename, directory="/etc/leapp/files", service=None, allow_empty=False):
        fetch._raise_error('pes-data.json', 'epic fail!')

    monkeypatch.setattr(fetch, 'read_or_fetch', read_or_fetch_mocked)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    with pytest.raises(StopActorExecutionError):
        get_events('/etc/leapp', 'pes-data.json')


def test_add_output_pkgs_to_transaction_conf():
    """
    Verifies that the add_output_pkgs_to_transaction_conf correctly modifies to_remove field based
    on the supplied events.
    """
    events = [
        Event(1, Action.SPLIT,
              {Package('split_in', 'repo', None)},
              {Package('split_out1', 'repo', None), Package('split_out2', 'repo', None)},
              (7, 6), (8, 0), []),
        Event(2, Action.MERGED,
              {Package('merge_in1', 'repo', None), Package('merge_in2', 'repo', None)},
              {Package('merge_out', 'repo', None)},
              (7, 6), (8, 0), []),
        Event(3, Action.RENAMED,
              {Package('renamed_in', 'repo', None)},
              {Package('renamed_out', 'repo', None)},
              (7, 6), (8, 0), []),
        Event(4, Action.REPLACED,
              {Package('replaced_in', 'repo', None)},
              {Package('replaced_out', 'repo', None)},
              (7, 6), (8, 0), []),
    ]

    conf_empty = RpmTransactionTasks()
    add_output_pkgs_to_transaction_conf(conf_empty, events)
    assert conf_empty.to_remove == []

    conf_split = RpmTransactionTasks(to_remove=['split_in'])
    add_output_pkgs_to_transaction_conf(conf_split, events)
    assert sorted(conf_split.to_remove) == ['split_in', 'split_out1', 'split_out2']

    conf_merged_incomplete = RpmTransactionTasks(to_remove=['merge_in1'])
    add_output_pkgs_to_transaction_conf(conf_merged_incomplete, events)
    assert conf_merged_incomplete.to_remove == ['merge_in1']

    conf_merged = RpmTransactionTasks(to_remove=['merge_in1', 'merge_in2'])
    add_output_pkgs_to_transaction_conf(conf_merged, events)
    assert sorted(conf_merged.to_remove) == ['merge_in1', 'merge_in2', 'merge_out']

    conf_renamed = RpmTransactionTasks(to_remove=['renamed_in'])
    add_output_pkgs_to_transaction_conf(conf_renamed, events)
    assert sorted(conf_renamed.to_remove) == ['renamed_in', 'renamed_out']

    conf_replaced = RpmTransactionTasks(to_remove=['replaced_in'])
    add_output_pkgs_to_transaction_conf(conf_replaced, events)
    assert sorted(conf_replaced.to_remove) == ['replaced_in', 'replaced_out']


def test_filter_events_by_architecture():
    """
    Verifies that the packages are correctly filtered based on the architecture.
    """
    events = [
        Event(1, Action.PRESENT, {Package('pkg1', 'repo', None)}, set(), (7, 6), (8, 0), ['arch1']),
        Event(2, Action.PRESENT, {Package('pkg2', 'repo', None)}, set(), (7, 6), (8, 0), ['arch2', 'arch1', 'arch3']),
        Event(3, Action.PRESENT, {Package('pkg3', 'repo', None)}, set(), (7, 6), (8, 0), ['arch2', 'arch3', 'arch4']),
        Event(4, Action.PRESENT, {Package('pkg4', 'repo', None)}, set(), (7, 6), (8, 0), [])
    ]

    filtered = filter_events_by_architecture(events, 'arch1')
    assert {Package('pkg1', 'repo', None)} in [event.in_pkgs for event in filtered]
    assert {Package('pkg2', 'repo', None)} in [event.in_pkgs for event in filtered]
    assert {Package('pkg3', 'repo', None)} not in [event.in_pkgs for event in filtered]
    assert {Package('pkg4', 'repo', None)} in [event.in_pkgs for event in filtered]


def test_filter_events_by_releases():
    """
    Tests whether the events are correctly filtered based on the relevant supplied releases.
    """
    events = [
        Event(1, Action.PRESENT, {Package('pkg1', 'repo', None)}, set(), (7, 6), (7, 7), []),
        Event(2, Action.PRESENT, {Package('pkg2', 'repo', None)}, set(), (7, 7), (7, 8), []),
        Event(3, Action.PRESENT, {Package('pkg3', 'repo', None)}, set(), (7, 8), (8, 0), []),
        Event(4, Action.PRESENT, {Package('pkg4', 'repo', None)}, set(), (8, 0), (8, 1), []),
        Event(5, Action.PRESENT, {Package('pkg5', 'repo', None)}, set(), (8, 1), (8, 2), [])
    ]

    filtered = filter_events_by_releases(events, [(7, 6), (7, 7), (8, 0), (8, 3)])
    assert {Package('pkg1', 'repo', None)} in [event.in_pkgs for event in filtered]
    assert {Package('pkg2', 'repo', None)} not in [event.in_pkgs for event in filtered]
    assert {Package('pkg3', 'repo', None)} in [event.in_pkgs for event in filtered]
    assert {Package('pkg4', 'repo', None)} not in [event.in_pkgs for event in filtered]
    assert {Package('pkg5', 'repo', None)} not in [event.in_pkgs for event in filtered]


@pytest.mark.parametrize(('src_version', 'dst_version', 'expected_releases'),
                         [('7.9', '8.6', [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6)]),
                          ('8.6', '9.0', [(9, 0)])])
def test_filter_irrelevant_releases(monkeypatch, src_version, dst_version, expected_releases):
    """
    Tests that all releases that happened before source version or after the target version are filtered out.
    """

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_version, dst_ver=dst_version))
    releases = [
        (7, 6), (7, 7), (7, 8), (7, 9), (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (9, 0), (9, 1)
    ]
    filtered_releases = filter_irrelevant_releases(releases)
    assert filtered_releases == expected_releases


def test_drop_conflicting_release_events():
    """
    Tests whether correct events are dropped from conflicting release events.
    From conflicting events only the one with highest target release should be kept.
    """

    conflict1a = Event(1, Action.PRESENT, {Package('pkg1', 'repo', None)}, set(), (7, 6), (8, 0), [])
    conflict1b = Event(2, Action.REPLACED, {Package('pkg1', 'repo', None)}, set(), (7, 6), (8, 2), [])
    conflict1c = Event(3, Action.REMOVED, {Package('pkg1', 'repo', None)}, set(), (7, 6), (8, 1), [])
    conflict2a = Event(4, Action.REMOVED, {Package('pkg2a', 'repo', None)}, set(), (7, 6), (8, 0), [])
    conflict2b = Event(5, Action.REPLACED,
                       {Package('pkg2a', 'repo', None)}, {Package('pkg2b', 'repo', None)},
                       (7, 6), (8, 1), [])
    # two input packages
    conflict3a = Event(6, Action.MERGED,
                       {Package('pkg3a', 'repo', None), Package('pkg3b', 'repo', None)},
                       {Package('pkg3c', 'repo', None)},
                       (7, 6), (8, 0), [])
    conflict3b = Event(7, Action.MERGED,
                       {Package('pkg3a', 'repo', None), Package('pkg3b', 'repo', None)},
                       {Package('pkg3d', 'repo', None)},
                       (7, 6), (8, 1), [])
    # these two can't be chained, don't remove anything
    okay1a = Event(8, Action.REPLACED,
                   {Package('pkg4a', 'repo', None)}, {Package('pkg4b', 'repo', None)},
                   (7, 6), (8, 0), [])
    okay1b = Event(9, Action.REPLACED,
                   {Package('pkg4b', 'repo', None)}, {Package('pkg4c', 'repo', None)},
                   (8, 0), (8, 1), [])

    events = [conflict1a, conflict1b, conflict1c, conflict2a, conflict2b, conflict3a, conflict3b, okay1a, okay1b]
    drop_conflicting_release_events(events)

    for event in [conflict1b, conflict2b, conflict3b, okay1a, okay1b]:
        assert event in events
    for event in [conflict1a, conflict1c, conflict2a, conflict3a]:
        assert event not in events


def test_process_modular_events(monkeypatch):
    monkeypatch.setattr(peseventsscanner, 'map_repositories', lambda x: x)
    monkeypatch.setattr(peseventsscanner, 'filter_out_pkgs_in_blacklisted_repos', lambda x: x)

    events = [
        # match the right modular package without touching the ones with absent or different module/stream
        # in practice, installed packages can't have the same name, just testing that it matches the right one
        Event(1, Action.REMOVED, {Package('removed', 'repo', ('module', '42'))}, set(), (8, 4), (9, 0), []),
        Event(2, Action.SPLIT,
              {Package('split_in', 'repo', ('splitin', 'foo'))},
              {Package('split_out1', 'repo', None), Package('split_out2', 'repo', ('splitout', 'foo'))},
              (8, 4), (9, 0), []),
        Event(3, Action.SPLIT,
              {Package('split_in', 'repo', ('splitin', 'bar'))},
              {Package('split_out3', 'repo', None), Package('split_out2', 'repo', ('splitout', 'bar'))},
              (8, 4), (9, 0), []),
    ]
    installed_pkgs = {('removed', ('module', '42')),
                      ('removed', ('model', '42')),
                      ('removed', ('module', '420')),
                      ('removed', None),
                      ('split_in', ('splitin', 'foo'))}

    tasks = process_events([(9, 0)], events, installed_pkgs)

    assert ('removed', ('module', '42')) in tasks[Task.REMOVE]  # name, module and stream match
    assert ('removed', ('model', '42')) not in tasks[Task.REMOVE]  # different module
    assert ('removed', ('module', '420')) not in tasks[Task.REMOVE]  # different stream
    assert ('removed', None) not in tasks[Task.REMOVE]  # no module stream

    assert ('split_in', ('splitin', 'foo')) in tasks[Task.REMOVE]
    assert ('split_out1', None) in tasks[Task.INSTALL]
    assert ('split_out2', ('splitout', 'foo')) in tasks[Task.INSTALL]
    assert ('split_in', ('splitin', 'bar')) not in tasks[Task.REMOVE]
    assert ('split_out3', None) not in tasks[Task.INSTALL]
    assert ('split_out2', ('splitout', 'bar')) not in tasks[Task.INSTALL]


@ pytest.mark.parametrize(('installed_pkgs', 'expected_relevance'),
                          [({('pkg1', None), ('pkg2', None)}, True),
                          ({('pkg2', None)}, True),
                          ({('pkg0', None)}, True),
                          ({('pkg1', 'wuzza:11')}, True),
                          ({('pkg2', 'wuzza:11')}, True),
                          ({('pkg1', 'wuzza:11'), ('pkg2', 'wuzza:11')}, True),
                          ({('pkg0', 'wuzza:11')}, False),
                          (set(), False)])
def test_merge_events_relevance_assessment(monkeypatch, installed_pkgs, expected_relevance):
    """
    Verifies that the relevance of the MERGED events is correctly assessed when processing events.
    """
    monkeypatch.setattr(peseventsscanner, 'map_repositories', lambda x: x)
    monkeypatch.setattr(peseventsscanner, 'filter_out_pkgs_in_blacklisted_repos', lambda x: x)

    events = [
        Event(
            1, Action.REPLACED,
            {Package('pkg0', 'repo-in', None)},
            {Package('pkg4', 'repo-out', None)},
            (7, 8), (7, 9), []
        ),
        Event(
            2, Action.MERGED,
            {Package('pkg1', 'repo-in', None), Package('pkg2', 'repo-in', None)},
            {Package('pkg3', 'repo-out', None)},
            (7, 9), (8, 0), [],
        ),
        Event(
            3, Action.MERGED,
            {Package('pkg1', 'repo-in', 'wuzza:11'), Package('pkg2', 'repo-in', 'wuzza:11')},
            {Package('pkg3', 'repo-out', None)},
            (7, 9), (8, 0), [],
        )
    ]

    tasks = process_events([(7, 9), (8, 0)], events, installed_pkgs)

    if expected_relevance:
        assert not set(tasks[Task.INSTALL].keys()) - {('pkg3', None), ('pkg4', None)}
        removed_packages = set()
        if any(p[1] for p in installed_pkgs):
            removed_packages = installed_pkgs
        if ('pkg0', None) in installed_pkgs:
            removed_packages.add(('pkg0', None))
        if ('pkg1', None) in installed_pkgs or ('pkg2', None) in installed_pkgs:
            removed_packages.add(('pkg1', None))
            removed_packages.add(('pkg2', None))

        assert not set(tasks[Task.REMOVE].keys()) - removed_packages
    else:
        assert not tasks[Task.INSTALL]
        assert not tasks[Task.REMOVE]
