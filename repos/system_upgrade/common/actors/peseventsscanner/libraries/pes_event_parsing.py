import json
import os
from collections import defaultdict, namedtuple
from enum import IntEnum
from itertools import chain

from leapp import reporting
from leapp.exceptions import StopActorExecution
from leapp.libraries.common import fetch
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api

# NOTE(mhecko): The modulestream field contains a set of modulestreams until the very end when we generate a Package
# for every modulestream in this set.
_Package = namedtuple('Package', ['name',         # str
                                  'repository',   # str
                                  'modulestream'  # (str, str) or None
                                  ])


class Package(_Package):  # noqa: E0102; pylint: disable=function-redefined
    def __repr__(self):
        ms = ''
        if self.modulestream:
            # The package class contains multiple modulestreams until a package for every single of these modulestreams
            # is generated. We have to check whether modulestream in fact contains multiple modulestreams and handle it
            # accordingly, so that we print Package when debugging.
            if len(self.modulestream) == 2 and all((isinstance(item, str) for item in self.modulestream)):
                ms = '@{0}:{1}'.format(*self.modulestream)
            else:
                ms = '{{{0}}}'.format(','.join(str(item) for item in self.modulestream))
        return '{n}:{r}{ms}'.format(n=self.name, r=self.repository, ms=ms)

    def __hash__(self):
        return hash((self.name, self.modulestream))

    def __eq__(self, other):
        return (self.name, self.modulestream) == (other.name, other.modulestream)


Event = namedtuple('Event', ['id',            # int
                             'action',        # An instance of Action
                             'in_pkgs',       # A set of Package named tuples
                             'out_pkgs',      # A set of Package named tuples
                             'from_release',  # A tuple representing a release in format (major, minor)
                             'to_release',    # A tuple representing a release in format (major, minor)
                             'architectures'  # A list of strings representing architectures
                             ])


class Action(IntEnum):
    PRESENT = 0
    REMOVED = 1
    DEPRECATED = 2
    REPLACED = 3
    SPLIT = 4
    MERGED = 5
    MOVED = 6
    RENAMED = 7


def get_pes_events(pes_json_directory, pes_json_filename):
    """
    Get all the events from the source JSON file exported from PES.

    :return: List of Event tuples, where each event contains event type and input/output pkgs
    """
    try:
        all_events = parse_pes_events(fetch.read_or_fetch(pes_json_filename, directory=pes_json_directory,
                                                          allow_empty=True))
        arch = api.current_actor().configuration.architecture
        events_matching_arch = [e for e in all_events if not e.architectures or arch in e.architectures]
        return events_matching_arch
    except (ValueError, KeyError):
        title = 'Missing/Invalid PES data file ({}/{})'.format(pes_json_directory, pes_json_filename)
        summary = ('Read documentation at: https://access.redhat.com/articles/3664871 for more information ',
                   'about how to retrieve the files')
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.RelatedResource('file', os.path.join(pes_json_directory, pes_json_filename))
        ])
        raise StopActorExecution()


def generate_event_for_ms_mapping_entry(from_ms_to_ms_entry, event):
    from_modulestream, to_modulestreams = from_ms_to_ms_entry

    in_pkgs_matching_from_ms = {
        Package(p.name, p.repository, from_modulestream) for p in event.in_pkgs if from_modulestream in p.modulestream
    }

    # Out pkgs are a bit harder to pick, as there are more than one modulestreams in to_modulestreams
    out_pkgs_matching_to_ms = set()
    for pkg in event.out_pkgs:
        target_modulestreams = set(pkg.modulestream).intersection(to_modulestreams)
        if len(target_modulestreams) > 1:
            # This is not expected to happen. Produce a warning, but continue by picking a single of the modulestreams.
            api.current_logger().warning('Event {0} - output package {1} matches multiple to_modulestreams '
                                         ' when generating events per modulestream mapping.')
        if not target_modulestreams:
            # No target_modulestreams mean that this package should not be included in the resulting event
            continue

        target_modulestream = next(iter(target_modulestreams))
        out_pkgs_matching_to_ms.add(Package(pkg.name, pkg.repository, target_modulestream))

    return Event(
        event.id,
        event.action,
        in_pkgs_matching_from_ms,
        out_pkgs_matching_to_ms,
        event.from_release,
        event.to_release,
        event.architectures
    )


def event_by_modulestream_mapping(mapping, event):
    """
    Generate events with matching event.ID according to the the given modulestream mapping.

    Modulestream mapping allows for a compact symbolic representation of multiple events having the same input/output
    packages differing only in the modules they are in. For example consider event renaming package X with module
    streams [MSX0, MSX1], to a new package with the name Y and possible module streams [MSY0, MSY1]. The attached
    modulestream map {MSX0 -> MSY0, MSX1 -> MSY1} would mean that the renaming event represents two events --- one
    renaming (X, ms=MSX0) to (Y, ms=MSY0), and the second one renaming (X, ms=MSX1) to (Y, ms=MSY1).

    :param mapping: A dictionary mapping package's input modulestream to its output modulestreams.
    :param event: PES event that should be uncompressed.
    :returns: A list of generated PES events.
    """
    if not mapping:
        # In case there is no mapping, assume all is going to non modular
        mapping = defaultdict(set)
        for package in event.in_pkgs:
            for ms in package.modulestream or ():
                mapping[ms].add(None)

    return [generate_event_for_ms_mapping_entry(from_ms_to_ms_entry, event) for from_ms_to_ms_entry in mapping.items()]


def parse_pes_events(json_data):
    """
    Parse JSON data returning PES events

    :return: List of Event tuples, where each event contains event type and input/output pkgs
    """
    data = json.loads(json_data)
    if not isinstance(data, dict) or not data.get('packageinfo'):
        raise ValueError('Found PES data with invalid structure')

    return list(chain(*[parse_entry(entry) for entry in data['packageinfo']]))


def parse_entry(entry):
    """
    Parse PES event data

    :param entry: A dict with the following structure:
                  {
                      'action': 3,
                      'id': 15,
                      'initial_release': {  # can be None
                          'z_stream': None,
                          'major_version': 7,
                          'tag': None,
                          'os_name': 'RHEL',
                          'minor_version': 7
                      },
                      'release': {
                          'z_stream': None,
                          'major_version': 8,
                          'tag': None,
                          'os_name': 'RHEL',
                          'minor_version': 0
                      },
                      'in_packageset': {
                          'set_id': 20,
                          'package': [
                              {
                                  'name': 'espeak',
                                  'repository': 'rhel7-optional'
                              }
                          ]
                      },
                      'out_packageset': {  # can be None
                          'set_id': 21,
                          'package': [
                              {
                                  'name': 'espeak-ng',
                                  'repository': 'rhel8-AppStream'
                              }
                          ]
                      },
                      'architectures': [  # can be empty
                          'x86_64',
                          'aarch64',
                          'ppc64le',
                          's390x'
                      ]
                  }
    """

    event_id = entry.get('id') or 0

    action_id = entry['action']
    if action_id < 0 or action_id >= len(Action):
        raise ValueError('Found event with invalid action ID: {}'.format(action_id))
    action = Action(action_id)

    in_pkgs = parse_packageset(entry.get('in_packageset') or {})
    out_pkgs = parse_packageset(entry.get('out_packageset') or {})

    # parse_release handles missing release data, no need to supply a default value
    from_release = parse_release(entry.get('initial_release'))
    to_release = parse_release(entry.get('release'))

    architectures = entry.get('architectures') or []
    invalid_archs = tuple(arch for arch in architectures if arch not in architecture.ARCH_ACCEPTED)
    if invalid_archs:
        raise ValueError('Found event with invalid architecture{0}: {1}'.format('s' if len(invalid_archs) > 1 else '',
                                                                                ', '.join(invalid_archs)))

    # Parse modulestream maps
    modulestream_map_entry = entry.get('modulestream_maps') or []

    modulestream_maps = defaultdict(set)
    for mapping_entry in modulestream_map_entry:
        in_ms_entry = mapping_entry.get('in_modulestream', {})
        in_modulestream = (in_ms_entry.get('name'), in_ms_entry.get('stream')) if in_ms_entry else None

        out_ms_entry = mapping_entry.get('out_modulestream', {})
        out_modulestream = (out_ms_entry.get('name'), out_ms_entry.get('stream')) if out_ms_entry else None

        # One modulestream might have more than one output modulestream - eg. the output packages of split belong to
        # different modulestreams: (pkg_in, ms1) is split to (pkg_out1, ms2), (pkg_out2, ms3). Therefore, we need to
        # collect for every input modulestream all the output modulestreams it maps to.
        modulestream_maps[in_modulestream].add(out_modulestream)

    return event_by_modulestream_mapping(
        modulestream_maps,
        Event(event_id, action, in_pkgs, out_pkgs, from_release, to_release, architectures)
    )


def parse_packageset(packageset):
    """
    Get "input" or "output" packages and their repositories from each PES event.

    :return: set of Package tuples
    """
    packageset_pkgs = packageset.get('package', packageset.get('packages', []))
    parsed_pkgs = set()

    for package in packageset_pkgs:
        # The package can have either the modulestreams field (a list of modulestream entries)
        # or a modulestream entry containing a single module stream
        modulestream_entries = package.get('modulestreams')
        if not modulestream_entries:
            modulestream_entry = package.get('modulestream')
            if isinstance(modulestream_entry, dict):
                # There is only one module stream present
                modulestream_entries = (modulestream_entry,)

        if not modulestream_entries:
            modulestreams = (None, )
        else:
            modulestreams = tuple((ms['name'], ms['stream']) if ms else None for ms in modulestream_entries)

        pkg = Package(package['name'], package['repository'], modulestreams)
        parsed_pkgs.add(pkg)

    return parsed_pkgs


def parse_release(release):
    return (release['major_version'], release['minor_version']) if release else (0, 0)
