import os.path

import pytest

from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import library
from leapp.libraries.actor.library import (Event,
                                           add_output_pkgs_to_transaction_conf,
                                           filter_out_pkgs_in_blacklisted_repos,
                                           get_events,
                                           get_events_for_installed_pkgs_only,
                                           map_repositories, parse_action,
                                           parse_entry, parse_packageset,
                                           parse_pes_events_file,
                                           process_events,
                                           report_skipped_packages)
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api


class show_message_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, msg):
        self.called += 1
        self.msg = msg


class produce_mocked(object):
    def __init__(self):
        self.called = 0
        self.model_instances = []

    def __call__(self, *model_instances):
        self.called += 1
        self.model_instances.append(model_instances[0])


class report_generic_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, **report_fields):
        self.called += 1
        self.report_fields = report_fields


class get_repos_blacklisted_mocked():
    def __init__(self, blacklisted):
        self.blacklisted = blacklisted

    def __call__(self):
        return self.blacklisted


def test_parse_action(current_actor_context):
    assert parse_action(0) == 'Present'
    assert parse_action(1) == 'Removed'
    assert parse_action(2) == 'Deprecated'
    assert parse_action(3) == 'Replaced'
    assert parse_action(4) == 'Split'
    assert parse_action(5) == 'Merged'
    assert parse_action(6) == 'Moved'
    assert parse_action(7) == 'Renamed'

    with pytest.raises(ValueError):
        parse_action(-1)
        parse_action(8)


def test_parse_packageset(current_actor_context):
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo'}]}

    assert parse_packageset(pkgset) == {'pkg1': 'repo'}

    assert parse_packageset({}) == {}
    assert parse_packageset({'setid': 0}) == {}


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
    assert event.action == 'Split'
    assert event.in_pkgs == {'original': 'repo'}
    assert event.out_pkgs == {'split01': 'repo', 'split02': 'repo'}

    entry = {
        'action': 1,
        'in_packageset': {
            'package': [{'name': 'removed', 'repository': 'repo'}]}}

    event = parse_entry(entry)
    assert event.action == 'Removed'
    assert event.in_pkgs == {'removed': 'repo'}
    assert event.out_pkgs == {}


def test_parse_pes_events_file(current_actor_context):
    events = parse_pes_events_file('files/tests/sample01.json')
    assert len(events) == 2
    assert events[0].action == 'Split'
    assert events[0].in_pkgs == {'original': 'repo'}
    assert events[0].out_pkgs == {'split01': 'repo', 'split02': 'repo'}
    assert events[1].action == 'Removed'
    assert events[1].in_pkgs == {'removed': 'repo'}
    assert events[1].out_pkgs == {}


def test_get_events_for_installed_pkgs_only(monkeypatch):
    events = [
        Event('Split', {'original': 'repo'}, {'split01': 'repo', 'split02': 'repo'}),
        Event('Removed', {'removed': 'repo'}, {})]
    filtered = get_events_for_installed_pkgs_only(events, {'original'})

    assert len(filtered) == 1
    assert filtered[0].action == 'Split'
    assert filtered[0].in_pkgs == {'original': 'repo'}
    assert filtered[0].out_pkgs == {'split01': 'repo', 'split02': 'repo'}


def test_report_skipped_packages(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '1')
    report_skipped_packages('packages will not be installed:', ['skipped01', 'skipped02'])

    message = '2 packages will not be installed:\n- skipped01\n- skipped02'
    assert api.show_message.called == 1
    assert api.show_message.msg == message
    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'Packages will not be installed'
    assert reporting.report_generic.report_fields['summary'] == message


def test_report_skipped_packages_no_verbose_mode(monkeypatch):
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '0')
    report_skipped_packages('packages will not be installed:', ['skipped01', 'skipped02'])

    message = '2 packages will not be installed:\n- skipped01\n- skipped02'
    assert api.show_message.called == 0
    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'Packages will not be installed'
    assert reporting.report_generic.report_fields['summary'] == message


def test_filter_out_pkgs_in_blacklisted_repos(monkeypatch):
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setattr(library, 'get_repositories_blacklisted', get_repos_blacklisted_mocked(set(['blacklisted'])))
    monkeypatch.setenv('LEAPP_VERBOSE', '1')

    to_install = {
        'pkg01': 'repo01',
        'pkg02': 'repo02',
        'skipped01': 'blacklisted',
        'skipped02': 'blacklisted'}
    filter_out_pkgs_in_blacklisted_repos(to_install)

    msgs = [
        '2 packages will not be installed due to blacklisted repositories:',
        '- skipped01',
        '- skipped02']
    assert api.show_message.called == 1
    assert api.show_message.msg == '\n'.join(msgs)
    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['summary'] == '\n'.join(msgs)
    assert reporting.report_generic.report_fields['title'] == 'Packages will not be installed'

    assert to_install == {'pkg01': 'repo01', 'pkg02': 'repo02'}


def test_map_repositories(monkeypatch):
    monkeypatch.setattr(api, 'show_message', show_message_mocked())
    monkeypatch.setattr(library, 'REPOSITORIES_MAPPING', {'repo': 'mapped'})
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    monkeypatch.setenv('LEAPP_VERBOSE', '1')

    to_install = {
        'pkg01': 'repo',
        'pkg02': 'repo',
        'skipped01': 'not_mapped',
        'skipped02': 'not_mapped'}
    map_repositories(to_install)

    msgs = [
        '2 packages will not be installed due to not mapped repositories:',
        '- skipped01',
        '- skipped02']
    assert api.show_message.called == 1
    assert api.show_message.msg == '\n'.join(msgs)
    assert reporting.report_generic.called == 1
    assert reporting.report_generic.report_fields['title'] == 'Packages will not be installed'
    assert reporting.report_generic.report_fields['summary'] == '\n'.join(msgs)

    assert to_install == {'pkg01': 'mapped', 'pkg02': 'mapped'}


def test_process_events(monkeypatch):
    monkeypatch.setattr(library, 'REPOSITORIES_MAPPING', {'repo': 'mapped'})
    monkeypatch.setattr(library, 'get_repositories_blacklisted', get_repos_blacklisted_mocked(set()))

    events = [
        Event('Split', {'original': 'repo'}, {'split01': 'repo', 'split02': 'repo'}),
        Event('Removed', {'removed': 'repo'}, {})]
    to_install, to_remove = process_events(events, {})

    assert len(to_install) == 2
    assert to_install == {'split02': 'mapped', 'split01': 'mapped'}
    assert len(to_remove) == 2
    assert to_remove == {'removed': 'repo', 'original': 'repo'}


def test_get_events(monkeypatch):
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())

    with pytest.raises(StopActorExecution):
        get_events('files/tests/sample02.json')
    assert reporting.report_generic.called == 1
    assert 'inhibitor' in reporting.report_generic.report_fields['flags']

    reporting.report_generic.called = 0
    reporting.report_generic.model_instances = []
    with pytest.raises(StopActorExecution):
        get_events('files/tests/sample03.json')
    assert reporting.report_generic.called == 1
    assert 'inhibitor' in reporting.report_generic.report_fields['flags']


def test_pes_data_not_found(monkeypatch):
    def file_not_exists(_filepath):
        return False
    monkeypatch.setattr(os.path, 'isfile', file_not_exists)
    monkeypatch.setattr(reporting, 'report_generic', report_generic_mocked())
    with pytest.raises(StopActorExecution):
        get_events('/etc/leapp/pes-data.json')
    assert reporting.report_generic.called == 1
    assert 'inhibitor' in reporting.report_generic.report_fields['flags']


def test_add_output_pkgs_to_transaction_conf():
    events = [
        Event('Split', {'split_in': 'repo'}, {'split_out1': 'repo', 'split_out2': 'repo'}),
        Event('Merged', {'merged_in1': 'repo', 'merged_in2': 'repo'}, {'merged_out': 'repo'}),
        Event('Renamed', {'renamed_in': 'repo'}, {'renamed_out': 'repo'}),
        Event('Replaced', {'replaced_in': 'repo'}, {'replaced_out': 'repo'}),
    ]

    conf_empty = RpmTransactionTasks()
    add_output_pkgs_to_transaction_conf(conf_empty, events)
    assert conf_empty.to_remove == []

    conf_split = RpmTransactionTasks(to_remove=['split_in'])
    add_output_pkgs_to_transaction_conf(conf_split, events)
    assert sorted(conf_split.to_remove) == ['split_in', 'split_out1', 'split_out2']

    conf_merged_incomplete = RpmTransactionTasks(to_remove=['merged_in1'])
    add_output_pkgs_to_transaction_conf(conf_merged_incomplete, events)
    assert conf_merged_incomplete.to_remove == ['merged_in1']

    conf_merged = RpmTransactionTasks(to_remove=['merged_in1', 'merged_in2'])
    add_output_pkgs_to_transaction_conf(conf_merged, events)
    assert sorted(conf_merged.to_remove) == ['merged_in1', 'merged_in2', 'merged_out']

    conf_renamed = RpmTransactionTasks(to_remove=['renamed_in'])
    add_output_pkgs_to_transaction_conf(conf_renamed, events)
    assert sorted(conf_renamed.to_remove) == ['renamed_in', 'renamed_out']

    conf_replaced = RpmTransactionTasks(to_remove=['replaced_in'])
    add_output_pkgs_to_transaction_conf(conf_replaced, events)
    assert sorted(conf_replaced.to_remove) == ['replaced_in', 'replaced_out']
