import os.path

import pytest

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import peseventsscanner
from leapp.libraries.actor.peseventsscanner import (
    SKIPPED_PKGS_MSG,
    Package,
    Action,
    Event,
    Task,
    add_output_pkgs_to_transaction_conf,
    drop_conflicting_release_events,
    filter_out_pkgs_in_blacklisted_repos,
    filter_events_by_architecture,
    filter_events_by_releases,
    filter_releases,
    get_events,
    map_repositories, parse_action,
    parse_entry, parse_packageset,
    parse_pes_events,
    process_events,
    report_skipped_packages)
from leapp import reporting
from leapp.libraries.common import fetch
from leapp.libraries.common.testutils import produce_mocked, create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import RpmTransactionTasks

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
    assert Package('pkg1', 'repo', None) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


def test_parse_packageset_modular(current_actor_context):
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo', 'modulestream': None},
                          {'name': 'pkg2', 'repository': 'Repo', 'modulestream': {
                              'name': 'hey', 'stream': 'lol'
                          }}]}

    parsed = parse_packageset(pkgset)
    assert len(parsed) == 2
    assert Package('pkg1', 'repo', None) in parsed
    assert Package('pkg2', 'repo', ('hey', 'lol')) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


def test_parse_entry(current_actor_context):
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
    assert event.in_pkgs == {Package('original', 'repo', None)}
    assert event.out_pkgs == {Package('split01', 'repo', None), Package('split02', 'repo', None)}

    entry = {
        'action': 1,
        'in_packageset': {
            'package': [{'name': 'removed', 'repository': 'repo'}]}}

    event = parse_entry(entry)
    assert event.action == Action.REMOVED
    assert event.in_pkgs == {Package('removed', 'repo', None)}
    assert event.out_pkgs == set()


def test_parse_pes_events(current_actor_context):
    with open(os.path.join(CUR_DIR, 'files/sample01.json')) as f:
        events = parse_pes_events(f.read())
    assert len(events) == 2
    assert events[0].action == Action.SPLIT
    assert events[0].in_pkgs == {Package('original', 'repo', None)}
    assert events[0].out_pkgs == {Package('split01', 'repo', None), Package('split02', 'repo', None)}
    assert events[1].action == Action.REMOVED
    assert events[1].in_pkgs == {Package('removed', 'repo', None)}
    assert events[1].out_pkgs == set()


def test_report_skipped_packages(monkeypatch, caplog):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    report_skipped_packages(
        title='Packages will not be installed',
        message='packages will not be installed:',
        package_repo_pairs=[('skipped01', 'bad_repo01'), ('skipped02', 'bad_repo02')]
    )

    message = (
        '2 packages will not be installed:\n'
        '- skipped01 (repoid: bad_repo01)\n'
        '- skipped02 (repoid: bad_repo02)'
    )
    assert message in caplog.messages
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'Packages will not be installed'
    assert reporting.create_report.report_fields['summary'] == message


def test_report_skipped_packages_no_verbose_mode(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '0')
    report_skipped_packages(
        title='Packages will not be installed',
        message='packages will not be installed:',
        package_repo_pairs=[('skipped01', 'bad_repo01'), ('skipped02', 'bad_repo02')]
    )

    message = (
        '2 packages will not be installed:\n'
        '- skipped01 (repoid: bad_repo01)\n'
        '- skipped02 (repoid: bad_repo02)'
    )
    assert api.show_message.called == 0
    assert reporting.create_report.called == 1
    assert reporting.create_report.report_fields['title'] == 'Packages will not be installed'
    assert reporting.create_report.report_fields['summary'] == message


def test_filter_out_pkgs_in_blacklisted_repos(monkeypatch, caplog):
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
    installed_pkgs = {'sip', 'sip-devel'}

    tasks = process_events([(8, 0)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {'python3-sip-devel': 'repo', 'python3-pyqt5-sip': 'repo', 'python3-sip': 'repo'}
    assert tasks[Task.REMOVE] == {'sip-devel': 'repo'}
    assert tasks[Task.KEEP] == {'sip': 'repo'}


def test_map_repositories(monkeypatch, caplog):
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(peseventsscanner, '_get_repositories_mapping', lambda: {'repo': 'mapped'})
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
    monkeypatch.setattr(peseventsscanner, '_get_repositories_mapping', lambda: {'rhel8-repo': 'rhel8-mapped'})
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
    installed_pkgs = {'original', 'removed', 'present', 'reintroduced'}
    tasks = process_events([(8, 0), (8, 1)], events, installed_pkgs)

    assert tasks[Task.INSTALL] == {'split02': 'rhel8-mapped', 'split01': 'rhel8-mapped'}
    assert tasks[Task.REMOVE] == {'removed': 'rhel7-repo', 'original': 'rhel7-repo'}
    assert tasks[Task.KEEP] == {'present': 'rhel8-mapped', 'reintroduced': 'rhel8-mapped'}


def test_get_events(monkeypatch):
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


def test_filter_releases():
    releases = [(7, 6), (7, 7), (7, 8), (7, 9), (8, 0), (8, 1), (8, 2), (8, 3), (9, 0), (9, 1)]
    filtered_releases = filter_releases(releases, (7, 6), (8, 1))
    assert filtered_releases == [(7, 7), (7, 8), (7, 9), (8, 0), (8, 1)]


def test_drop_conflicting_release_events():
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
