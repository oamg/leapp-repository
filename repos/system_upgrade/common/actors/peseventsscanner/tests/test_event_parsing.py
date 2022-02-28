import os.path
from collections import namedtuple

import pytest

from leapp.libraries.actor.pes_event_parsing import (
    Action,
    Event,
    Package,
    parse_entry,
    parse_packageset,
    parse_pes_events
)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_parse_packageset(current_actor_context):
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo'}]}

    parsed = parse_packageset(pkgset)
    assert len(parsed) == 1
    assert Package('pkg1', 'Repo', (None,)) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


def test_parse_packageset_modular(current_actor_context):
    modulestreams = [{'name': 'hey', 'stream': 'lol1'}, {'name': 'hey', 'stream': 'lol2'}]
    pkgset = {'package': [{'name': 'pkg1', 'repository': 'Repo', 'modulestreams': [None]},
                          {'name': 'pkg2', 'repository': 'Repo', 'modulestreams': modulestreams}]}

    parsed = parse_packageset(pkgset)
    assert len(parsed) == 2
    assert Package('pkg1', 'Repo', (None,)) in parsed
    assert Package('pkg2', 'Repo', (('hey', 'lol1'), ('hey', 'lol2'))) in parsed

    assert parse_packageset({}) == set()
    assert parse_packageset({'set_id': 0}) == set()


PARSE_ENTRY_INPUTS = [
    (
        # Input
        {
            'action': 4,
            'architectures': ['x86_64', 's390x'],
            'in_packageset': {
                'package': [{'name': 'original', 'repository': 'repo'}]
            },
            'out_packageset': {
                'package': [{'name': 'split01', 'repository': 'repo'}, {'name': 'split02', 'repository': 'repo'}]
            }
        },
        # Expected output
        [
            Event(action=Action.SPLIT, architectures=['x86_64', 's390x'], from_release=(0, 0), to_release=(0, 0), id=0,
                  in_pkgs={Package('original', 'repo', None)},
                  out_pkgs={Package('split01', 'repo', None), Package('split02', 'repo', None)})
        ]
    ),
    (
        # Input
        {
            'action': 1,
            'in_packageset': {
                'package': [{'name': 'removed', 'repository': 'repo'}]
            }
        },
        # Expected output
        [
            Event(action=Action.REMOVED, architectures=[], from_release=(0, 0), to_release=(0, 0), id=0,
                  in_pkgs={Package('removed', 'repo', None)},
                  out_pkgs=set())
        ]
    ),
    ({'action': 10}, ValueError),  # Invalid action
    ({'action': -1}, ValueError),  # Invalid action
    (
        {'action': 1, 'architectures': ['ia-64']},  # Invalid architecture
        ValueError
    ),
]


@pytest.mark.parametrize(('pes_entry_data', 'expected_output'), PARSE_ENTRY_INPUTS)
def test_parse_entry(current_actor_context, pes_entry_data, expected_output):
    """
    Tests whether the PES event is correctly parsed from the supplied dictionary with the same
    structure as are the data stored inside the json.
    """

    if isinstance(expected_output, list):
        events = parse_entry(pes_entry_data)
        assert len(events) == len(expected_output)
        for event in events:
            assert event in expected_output
    else:
        with pytest.raises(expected_output):
            parse_entry(pes_entry_data)


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
