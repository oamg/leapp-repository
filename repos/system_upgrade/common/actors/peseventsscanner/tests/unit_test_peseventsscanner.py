import functools
import os.path

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import peseventsscanner
from leapp.libraries.actor.peseventsscanner import (
    Action,
    Event,
    SKIPPED_PKGS_MSG,
    Task,
    add_output_pkgs_to_transaction_conf,
    drop_conflicting_release_events,
    filter_events_by_architecture,
    filter_events_by_releases,
    filter_out_pkgs_in_blacklisted_repos,
    filter_releases_by_target,
    get_events,
    map_repositories, parse_action,
    parse_entry, parse_packageset,
    parse_pes_events,
    process_events,
    report_skipped_packages,
)
from leapp.libraries.common import fetch
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import PESIDRepositoryEntry, RpmTransactionTasks, RepositoriesMapping, RepoMapEntry

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

    assert parse_packageset(pkgset) == {'pkg1': 'Repo'}

    assert parse_packageset({}) == {}
    assert parse_packageset({'setid': 0}) == {}


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

    event = parse_entry(entry)
    assert event.action == Action.SPLIT
    assert event.in_pkgs == {'original': 'repo'}
    assert event.out_pkgs == {'split01': 'repo', 'split02': 'repo'}

    entry = {
        'action': 1,
        'in_packageset': {
            'package': [{'name': 'removed', 'repository': 'repo'}]}}

    event = parse_entry(entry)
    assert event.action == Action.REMOVED
    assert event.in_pkgs == {'removed': 'repo'}
    assert event.out_pkgs == {}


def test_parse_pes_events(current_actor_context):
    """
    Tests whether all events are correctly parsed from the provided string with the JSON data.
    """
    with open(os.path.join(CUR_DIR, 'files/sample01.json')) as f:
        events = parse_pes_events(f.read())
    assert len(events) == 2
    assert events[0].action == Action.SPLIT
    assert events[0].in_pkgs == {'original': 'repo'}
    assert events[0].out_pkgs == {'split01': 'repo', 'split02': 'repo'}
    assert events[1].action == Action.REMOVED
    assert events[1].in_pkgs == {'removed': 'repo'}
    assert events[1].out_pkgs == {}


@pytest.mark.parametrize('is_verbose_mode_on', [False, True])
def test_report_skipped_packages_no_verbose_mode(monkeypatch, caplog, is_verbose_mode_on):
    """
    Tests whether the report_skipped_packages function creates message of the expected form
    and that the function respects whether leapp is running in verbose mode.
    """
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    leapp_verbose = '1' if is_verbose_mode_on else '0'

    monkeypatch.setenv('LEAPP_VERBOSE', leapp_verbose)
    report_skipped_packages(
        title='Packages will not be installed',
        message='packages will not be installed:',
        package_repo_pairs=[('skipped01', 'bad_repo01'), ('skipped02', 'bad_repo02')]
    )

    # FIXME(pstodulk): this is obviously wrong. repoid is currently pesid.. so test
    # is incorrect, and code is incorrect. even the message is missleading.
    # this is going to be fixed in close future.
    message = (
        '2 packages will not be installed:\n'
        '- skipped01 (repoid: bad_repo01)\n'
        '- skipped02 (repoid: bad_repo02)'
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
        'pkg01': 'repo01',
        'pkg02': 'repo02',
        'skipped01': 'blacklisted',
        'skipped02': 'blacklisted',
    }
    msg = '2 {}\n{}'.format(
        SKIPPED_PKGS_MSG,
        '\n'.join(
            [
                '- {pkg} (repoid: {repo})'.format(pkg=pkg, repo=repo)
                for pkg, repo in filter(    # pylint: disable=deprecated-lambda
                    lambda item: item[1] == 'blacklisted', to_install.items()
                )
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

    assert to_install == {'pkg01': 'repo01', 'pkg02': 'repo02'}


def test_resolve_conflicting_requests(monkeypatch):
    """
    Verifies that the algorithm correctly resolves conflicting pes events.
    """
    monkeypatch.setattr(peseventsscanner, 'map_repositories', lambda x: x)
    monkeypatch.setattr(peseventsscanner, 'filter_out_pkgs_in_blacklisted_repos', lambda x: x)

    events = [
        Event(1, Action.SPLIT, {'sip-devel': 'repo'}, {'python3-sip-devel': 'repo', 'sip': 'repo'},
              (7, 6), (8, 0), []),
        Event(2, Action.SPLIT, {'sip': 'repo'}, {'python3-pyqt5-sip': 'repo', 'python3-sip': 'repo'},
              (7, 6), (8, 0), [])]
    installed_pkgs = {'sip', 'sip-devel'}

    tasks = process_events([(8, 0)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {'python3-sip-devel': 'repo', 'python3-pyqt5-sip': 'repo', 'python3-sip': 'repo'}
    assert tasks[Task.REMOVE] == {'sip-devel': 'repo'}
    assert tasks[Task.KEEP] == {'sip': 'repo'}


@pytest.mark.parametrize(('source_repoid', 'expected_target_repoid'),
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

    event = Event(1, Action.MOVED, {'test-pkg': 'rhel7-base'}, {'test-pkg': 'rhel8-CRB'},
                  (7, 9), (8, 0), [])
    installed_pkgs = {'test-pkg'}

    tasks = process_events([(8, 0)], [event], installed_pkgs)

    assert tasks[Task.KEEP] == {'test-pkg': expected_target_repoid}


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
        'pkg01': 'repo',
        'pkg02': 'repo',
        'skipped01': 'not_mapped',
        'skipped02': 'not_mapped'}
    map_repositories(to_install)

    msg = (
        '2 packages may not be installed or upgraded due to repositories unknown to leapp:\n'
        '- skipped01 (repoid: not_mapped)\n'
        '- skipped02 (repoid: not_mapped)'
    )
    assert msg in caplog.messages
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == (
        'Packages from unknown repositories may not be installed'
    )
    assert reporting.create_report.report_fields['summary'] == msg

    assert to_install == {'pkg01': 'mapped', 'pkg02': 'mapped'}


def test_process_events(monkeypatch):
    """
    Verifies that the event processing algorithm works as expected.
    """
    monkeypatch.setattr(peseventsscanner,
                        '_get_repositories_mapping',
                        lambda dummy_target_pesids: {'rhel8-repo': 'rhel8-mapped'})
    monkeypatch.setattr(peseventsscanner, 'get_repositories_blacklisted', get_repos_blacklisted_mocked(set()))

    events = [
        Event(1, Action.SPLIT, {'original': 'rhel7-repo'}, {'split01': 'rhel8-repo', 'split02': 'rhel8-repo'},
              (7, 6), (8, 0), []),
        Event(2, Action.REMOVED, {'removed': 'rhel7-repo'}, {}, (7, 6), (8, 0), []),
        Event(3, Action.PRESENT, {'present': 'rhel8-repo'}, {}, (7, 6), (8, 0), []),
        # this package is present at the start, gets removed and then reintroduced
        Event(4, Action.REMOVED, {'reintroduced': 'rhel7-repo'}, {}, (7, 6), (8, 0), []),
        Event(5, Action.PRESENT, {'reintroduced': 'rhel8-repo'}, {}, (8, 0), (8, 1), []),
        # however, this package was never there
        Event(6, Action.REMOVED, {'neverthere': 'rhel7-repo'}, {}, (7, 6), (8, 0), []),
        Event(7, Action.PRESENT, {'neverthere': 'rhel8-repo'}, {}, (8, 0), (8, 1), [])]
    installed_pkgs = {'original', 'removed', 'present', 'reintroduced'}
    tasks = process_events([(8, 0), (8, 1)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {'split02': 'rhel8-mapped', 'split01': 'rhel8-mapped'}
    assert tasks[Task.REMOVE] == {'removed': 'rhel7-repo', 'original': 'rhel7-repo'}
    assert tasks[Task.KEEP] == {'present': 'rhel8-mapped', 'reintroduced': 'rhel8-mapped'}


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
        Event(1, Action.SPLIT, {'split_in': 'repo'}, {'split_out1': 'repo', 'split_out2': 'repo'}, (7, 6), (8, 0), []),
        Event(2, Action.MERGED, {'merge_in1': 'repo', 'merge_in2': 'repo'}, {'merge_out': 'repo'}, (7, 6), (8, 0), []),
        Event(3, Action.RENAMED, {'renamed_in': 'repo'}, {'renamed_out': 'repo'}, (7, 6), (8, 0), []),
        Event(4, Action.REPLACED, {'replaced_in': 'repo'}, {'replaced_out': 'repo'}, (7, 6), (8, 0), []),
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
        Event(1, Action.PRESENT, {'pkg1': 'repo'}, {}, (7, 6), (8, 0), ['arch1']),
        Event(2, Action.PRESENT, {'pkg2': 'repo'}, {}, (7, 6), (8, 0), ['arch2', 'arch1', 'arch3']),
        Event(3, Action.PRESENT, {'pkg3': 'repo'}, {}, (7, 6), (8, 0), ['arch2', 'arch3', 'arch4']),
        Event(4, Action.PRESENT, {'pkg4': 'repo'}, {}, (7, 6), (8, 0), [])
    ]

    filtered = filter_events_by_architecture(events, 'arch1')
    assert {'pkg1': 'repo'} in [event.in_pkgs for event in filtered]
    assert {'pkg2': 'repo'} in [event.in_pkgs for event in filtered]
    assert {'pkg3': 'repo'} not in [event.in_pkgs for event in filtered]
    assert {'pkg4': 'repo'} in [event.in_pkgs for event in filtered]


def test_filter_events_by_releases():
    """
    Tests whether the events are correctly filtered based on the relevant supplied releases.
    """
    events = [
        Event(1, Action.PRESENT, {'pkg1': 'repo'}, {}, (7, 6), (7, 7), []),
        Event(2, Action.PRESENT, {'pkg2': 'repo'}, {}, (7, 7), (7, 8), []),
        Event(3, Action.PRESENT, {'pkg3': 'repo'}, {}, (7, 8), (8, 0), []),
        Event(4, Action.PRESENT, {'pkg4': 'repo'}, {}, (8, 0), (8, 1), []),
        Event(5, Action.PRESENT, {'pkg5': 'repo'}, {}, (8, 1), (8, 2), [])
    ]

    filtered = filter_events_by_releases(events, [(7, 6), (7, 7), (8, 0), (8, 3)])
    assert {'pkg1': 'repo'} in [event.in_pkgs for event in filtered]
    assert {'pkg2': 'repo'} not in [event.in_pkgs for event in filtered]
    assert {'pkg3': 'repo'} in [event.in_pkgs for event in filtered]
    assert {'pkg4': 'repo'} not in [event.in_pkgs for event in filtered]
    assert {'pkg5': 'repo'} not in [event.in_pkgs for event in filtered]


def test_filter_releases_by_target():
    """
    Tests that all releases greater than the target gets correctly filtered out when using filter_releases_by_target.
    """
    releases = [(7, 6), (7, 7), (7, 8), (7, 9), (8, 0), (8, 1), (8, 2), (8, 3), (9, 0), (9, 1)]
    filtered_releases = filter_releases_by_target(releases, (8, 1))
    assert filtered_releases == [(7, 6), (7, 7), (7, 8), (7, 9), (8, 0), (8, 1)]


def test_drop_conflicting_release_events():
    """
    Tests whether correct events are dropped from conflicting release events.
    From conflicting events only the one with highest target release should be kept.
    """
    conflict1a = Event(1, Action.PRESENT, {'pkg1': 'repo'}, {}, (7, 6), (8, 0), [])
    conflict1b = Event(2, Action.REPLACED, {'pkg1': 'repo'}, {}, (7, 6), (8, 2), [])
    conflict1c = Event(3, Action.REMOVED, {'pkg1': 'repo'}, {}, (7, 6), (8, 1), [])
    conflict2a = Event(4, Action.REMOVED, {'pkg2a': 'repo'}, {}, (7, 6), (8, 0), [])
    conflict2b = Event(5, Action.REPLACED, {'pkg2a': 'repo'}, {'pkg2b': 'repo'}, (7, 6), (8, 1), [])
    # two input packages
    conflict3a = Event(6, Action.MERGED, {'pkg3a': 'repo', 'pkg3b': 'repo'}, {'pkg3c': 'repo'}, (7, 6), (8, 0), [])
    conflict3b = Event(7, Action.MERGED, {'pkg3a': 'repo', 'pkg3b': 'repo'}, {'pkg3d': 'repo'}, (7, 6), (8, 1), [])
    # these two can't be chained, don't remove anything
    okay1a = Event(8, Action.REPLACED, {'pkg4a': 'repo'}, {'pkg4b': 'repo'}, (7, 6), (8, 0), [])
    okay1b = Event(9, Action.REPLACED, {'pkg4b': 'repo'}, {'pkg4c': 'repo'}, (8, 0), (8, 1), [])

    events = [conflict1a, conflict1b, conflict1c, conflict2a, conflict2b, conflict3a, conflict3b, okay1a, okay1b]
    drop_conflicting_release_events(events)

    for event in [conflict1b, conflict2b, conflict3b, okay1a, okay1b]:
        assert event in events
    for event in [conflict1a, conflict1c, conflict2a, conflict3a]:
        assert event not in events
