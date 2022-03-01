import json
import os
from collections import defaultdict, namedtuple
from enum import IntEnum
from itertools import chain

from leapp import reporting
from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import peseventsscanner_repomap
from leapp.libraries.common import fetch
from leapp.libraries.common.config import architecture, version
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import (
    EnabledModules,
    InstalledRedHatSignedRPM,
    Module,
    PESIDRepositoryEntry,
    PESRpmTransactionTasks,
    RepositoriesBlacklisted,
    RepositoriesFacts,
    RepositoriesMapping,
    RepositoriesSetupTasks,
    RHUIInfo,
    RpmTransactionTasks
)

_Package = namedtuple('Package', ['name',         # str
                                  'repository',   # str
                                  'modulestream'  # (str, str) or None - a module stream
                                  ])


class Package(_Package):  # noqa: E0102; pylint: disable=function-redefined
    def __repr__(self):
        ms = ''
        if self.modulestream:
            ms = '@{0}:{1}'.format(*self.modulestream)
        return '{n}:{r}{ms}'.format(n=self.name, r=self.repository, ms=ms)


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


class Task(IntEnum):
    KEEP = 0
    INSTALL = 1
    REMOVE = 2

    def past(self):
        return ['kept', 'installed', 'removed'][self]


def pes_events_scanner(pes_json_directory, pes_json_filename):
    """Entrypoint to the library"""
    installed_pkgs = get_installed_pkgs()
    transaction_configuration = get_transaction_configuration()
    arch = api.current_actor().configuration.architecture
    events = get_events(pes_json_directory, pes_json_filename)
    releases = get_releases(events)

    filtered_releases = filter_irrelevant_releases(releases)
    filtered_events = filter_events_by_releases(events, filtered_releases)
    arch_events = filter_events_by_architecture(filtered_events, arch)

    add_output_pkgs_to_transaction_conf(transaction_configuration, arch_events)
    drop_conflicting_release_events(arch_events)
    tasks = process_events(filtered_releases, arch_events, installed_pkgs)
    filter_out_transaction_conf_pkgs(tasks, transaction_configuration)
    produce_messages(tasks)


def get_installed_pkgs():
    """
    Get installed Red Hat-signed packages.

    :return: A set of tuples holding installed Red Hat-signed package names and their module streams
    """
    installed_pkgs = set()

    installed_rh_signed_rpm_msgs = api.consume(InstalledRedHatSignedRPM)
    installed_rh_signed_rpm_msg = next(installed_rh_signed_rpm_msgs, None)
    if list(installed_rh_signed_rpm_msgs):
        api.current_logger().warning('Unexpectedly received more than one InstalledRedHatSignedRPM message.')
    if not installed_rh_signed_rpm_msg:
        raise StopActorExecutionError('Cannot parse PES data properly due to missing list of installed packages',
                                      details={'Problem': 'Did not receive a message with installed Red Hat-signed '
                                                          'packages (InstalledRedHatSignedRPM)'})
    for pkg in installed_rh_signed_rpm_msg.items:
        modulestream = None
        if pkg.module and pkg.stream:
            modulestream = (pkg.module, pkg.stream)
        installed_pkgs.add((pkg.name, modulestream))
    return installed_pkgs


def _get_enabled_repoids():
    """
    Collects repoids of all enabled repositories on the source system.

    :param repositories_facts: Iterable of RepositoriesFacts containing repositories related info about source system.
    :return: Set of all enabled repository IDs present on the source system.
    :rtype: Set[str]
    """
    enabled_repoids = set()
    for repos in api.consume(RepositoriesFacts):
        for repo_file in repos.repositories:
            for repo in repo_file.data:
                if repo.enabled:
                    enabled_repoids.add(repo.repoid)
    return enabled_repoids


def _get_repositories_mapping(target_pesids):
    """
    Get all repositories mapped from repomap file and map repositories id with respective names.

    :param target_pesids: The set of expected needed target PES IDs
    :return: Dictionary with all repositories mapped.
    """

    repositories_map_msgs = api.consume(RepositoriesMapping)
    repositories_map_msg = next(repositories_map_msgs, None)
    if list(repositories_map_msgs):
        api.current_logger().warning('Unexpectedly received more than one RepositoriesMapping message.')
    if not repositories_map_msg:
        raise StopActorExecutionError(
            'Cannot parse RepositoriesMapping data properly',
            details={'Problem': 'Did not receive a message with mapped repositories'}
        )

    rhui_info = next(api.consume(RHUIInfo), RHUIInfo(provider=''))

    repomap = peseventsscanner_repomap.RepoMapDataHandler(repositories_map_msg, cloud_provider=rhui_info.provider)
    # NOTE: We have to calculate expected target repositories
    # like in the setuptargetrepos actor. It's planned to handle this in different
    # way in future...
    enabled_repoids = _get_enabled_repoids()
    default_channels = peseventsscanner_repomap.get_default_repository_channels(repomap, enabled_repoids)
    repomap.set_default_channels(default_channels)

    exp_pesid_repos = repomap.get_expected_target_pesid_repos(enabled_repoids)
    # FIXME: this is hack now. In case some packages will need a repository
    # with pesid that is not mapped by default regarding the enabled repos,
    # let's use this one representative repository (baseos/appstream) to get
    # data for a guess of the best repository from the requires target pesid..
    # FIXME: this could now fail in case all repos are disabled...
    representative_repo = exp_pesid_repos.get(
        peseventsscanner_repomap.DEFAULT_PESID[get_target_major_version()], None
    )
    if not representative_repo:
        api.current_logger().warning('Cannot determine the representative target base repository.')
        api.current_logger().info(
            'Fallback: Create an artificial representative PESIDRepositoryEntry for the repository mapping'
        )
        representative_repo = PESIDRepositoryEntry(
            pesid=peseventsscanner_repomap.DEFAULT_PESID[get_target_major_version()],
            arch=api.current_actor().configuration.architecture,
            major_version=get_target_major_version(),
            repoid='artificial-repoid',
            repo_type='rpm',
            channel='ga',
            rhui='',
        )

    for pesid in target_pesids:
        if pesid in exp_pesid_repos:
            continue
        # some packages are moved to repos outside of default repomapping
        # try to find the best possible repo for them..
        # FIXME: HACK NOW
        # good way is to modify class to search repo with specific criteria..
        if not representative_repo:
            api.current_logger().warning(
                'Cannot find suitable repository for PES ID: {}'
                .format(pesid)
            )
            continue
        pesid_repo = repomap._find_repository_target_equivalent(representative_repo, pesid)

        if not pesid_repo:
            api.current_logger().warning(
                'Cannot find suitable repository for PES ID: {}'
                .format(pesid)
            )
            continue
        exp_pesid_repos[pesid] = pesid_repo

    # map just pesids with found repoids
    # {to_pesid: repoid}
    repositories_mapping = {}
    for pesid, repository in exp_pesid_repos.items():
        if pesid not in target_pesids:
            # We can skip this repo as it was not identified as needed during the processing of PES events
            continue
        if not repository:
            # TODO
            continue
        repositories_mapping[pesid] = repository.repoid

    return repositories_mapping


def get_transaction_configuration():
    """
    Get pkgs to install, keep and remove from the user configuration files in /etc/leapp/transaction/.

    These configuration files have higher priority than PES data.
    :return: RpmTransactionTasks model instance
    """
    transaction_configuration = RpmTransactionTasks()

    for tasks in api.consume(RpmTransactionTasks):
        transaction_configuration.to_install.extend(tasks.to_install)
        transaction_configuration.to_remove.extend(tasks.to_remove)
        transaction_configuration.to_keep.extend(tasks.to_keep)
    return transaction_configuration


def filter_irrelevant_releases(releases):
    """
    Filter releases that are not relevant to this IPU.

    Irrelevant releases are those that happened before the source version and after the target version.
    :param List[Tuple[int, int]] releases: A list containing all releases present in the PES events being processed.
    :returns: A list of releases relevant for the current IPU.
    """

    match_list = [
        '> {0}'.format(api.current_actor().configuration.version.source),
        '<= {0}'.format(api.current_actor().configuration.version.target)
    ]

    return [r for r in releases if version.matches_version(match_list, '{}.{}'.format(*r))]


def get_events(pes_json_directory, pes_json_filename):
    """
    Get all the events from the source JSON file exported from PES.

    :return: List of Event tuples, where each event contains event type and input/output pkgs
    """
    try:
        return parse_pes_events(
            fetch.read_or_fetch(pes_json_filename, directory=pes_json_directory, allow_empty=True))
    except (ValueError, KeyError):
        title = 'Missing/Invalid PES data file ({}/{})'.format(pes_json_directory, pes_json_filename)
        summary = 'Read documentation at: https://access.redhat.com/articles/3664871 for more information ' \
            'about how to retrieve the files'
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SANITY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.RelatedResource('file', os.path.join(pes_json_directory, pes_json_filename))
        ])
        raise StopActorExecution()


def get_releases(events):
    """
    Get all target releases from a list of events.

    :return: List of (major, minor) release tuples, sorted in ascending order
    """
    return sorted({event.to_release for event in events})


def filter_events_by_architecture(events, arch):
    return [e for e in events if not e.architectures or arch in e.architectures]


def filter_events_by_releases(events, releases):
    return [e for e in events if e.to_release in releases]


def event_for_modulestram_mapping(from_to, event):
    from_ms, to_ms = from_to or (None, None)
    return Event(
        event.id,
        event.action,
        {Package(p.name, p.repository, from_ms) for p in event.in_pkgs if from_ms in p.modulestream},
        {Package(p.name, p.repository, to_ms) for p in event.out_pkgs if to_ms in p.modulestream},
        event.from_release,
        event.to_release,
        event.architectures
    )


def event_by_modulestream_mapping(mapping, event):
    if not mapping:
        # In case there is no mapping, assume all is going to non modular
        mapping = {}
        for package in event.in_pkgs:
            for ms in package.modulestream or ():
                mapping[ms] = None
    return [event_for_modulestram_mapping((from_ms, to_ms), event) for from_ms, to_ms in mapping.items()]


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
    action = parse_action(entry['action'])
    in_pkgs = parse_packageset(entry.get('in_packageset') or {})
    out_pkgs = parse_packageset(entry.get('out_packageset') or {})
    from_release = parse_release(entry.get('initial_release') or {})
    to_release = parse_release(entry.get('release') or {})
    architectures = parse_architectures(entry.get('architectures') or [])
    modulestream_maps = parse_modulestream_maps(entry.get('modulestream_maps', []))
    return event_by_modulestream_mapping(
        modulestream_maps,
        Event(event_id, action, in_pkgs, out_pkgs, from_release, to_release, architectures)
    )


def parse_action(action_id):
    """Get event type name based on PES event's action id"""
    if action_id < 0 or action_id >= len(Action):
        raise ValueError('Found event with invalid action ID: {}'. format(action_id))
    return Action(action_id)


def parse_modulestream(package):
    # It is possible that modulestream is absent, but modulestreams exist,
    # which would refer to a list of modulestreams, if it is modulestream,
    # it is supposed to be only one.
    modulestreams = package.get('modulestreams')
    if not modulestreams:
        modulestreams = package.get('modulestream')
        if isinstance(modulestreams, dict):
            modulestreams = (modulestreams,)
    if not modulestreams:
        return (None,)
    return tuple((ms['name'], ms['stream']) if ms else None for ms in modulestreams)


def parse_package(package):
    return Package(package['name'], package['repository'], parse_modulestream(package))


def parse_packageset(packageset):
    """
    Get "input" or "output" packages and their repositories from each PES event.

    :return: set of Package tuples
    """
    return {parse_package(p) for p in packageset.get('package', packageset.get('packages', []))}


def parse_modulestream_maps(modulestream_maps):
    def convert(ms):
        if not ms:
            return None
        return tuple(ms.values())

    def in_out(mapping):
        return (convert(mapping.get('in_modulestream')), convert(mapping.get('out_modulestream')))
    return dict(in_out(mapping) for mapping in modulestream_maps or [])


def parse_release(release):
    return (release['major_version'], release['minor_version']) if release else (0, 0)


def parse_architectures(architectures):
    for arch in architectures:
        if arch not in architecture.ARCH_ACCEPTED:
            raise ValueError('Found event with invalid architecture: {}'. format(arch))
    return architectures


def is_event_relevant(event, installed_pkgs, tasks):
    """Determine if event is applicable given the installed packages and tasks planned so far."""
    if event.action == Action.MERGED:
        # Merge events have different relevance criteria - it is sufficient for any
        # of their input packages to be installed in order for them to be relevant.
        in_pkgs_not_removed = {(p.name, p.modulestream) for p in event.in_pkgs} - set(tasks[Task.REMOVE].keys())
        pkgs_installed = installed_pkgs | set(tasks[Task.INSTALL].keys())
        in_pkgs_installed = in_pkgs_not_removed & pkgs_installed
        return bool(in_pkgs_installed)

    for package in [(p.name, p.modulestream) for p in event.in_pkgs]:
        if package in tasks[Task.REMOVE] and event.action != Action.PRESENT:
            return False
        if package not in installed_pkgs and package not in tasks[Task.INSTALL]:
            return False
    return True


def add_packages_to_tasks(tasks, packages, task_type):
    if packages:
        api.current_logger().debug('{v:7} {p}'.format(
            v=task_type.name, p=', '.join([p.__repr__() for p in packages])))
        for p in packages:
            tasks[task_type][(p.name, p.modulestream)] = p.repository


def _package_to_str(package):
    """
    Represent a package tuple with a string hash.

    Example: in: Package('mesa-libwayland-egl-devel', 'rhel7-optional', ('wayland', '4.2'))
             out: 'mesa-libwayland-egl-devel:rhel7-optional:wayland:4.2'
    """
    return '{n}:{ms}:{r}'.format(n=package.name,
                                 r=package.repository,
                                 ms=':'.join(package.modulestream) if package.modulestream else 'None')


def _packages_to_str(packages):
    """
    Represent a set of packages with a string hash.

    Example: in: {Package('mesa-libwayland-egl-devel', 'rhel7-optional', ('wayland', '4.2')),
                  Package('wayland-devel', 'rhel7-base', None)}
             out: 'mesa-libwayland-egl-devel:rhel7-optional:wayland:4.2,wayland-devel:rhel7-base:None'
    """
    return ','.join(_package_to_str(p) for p in sorted(packages))


def drop_conflicting_release_events(events):
    """
    In case of events with identical initial release and input packages, drop those with older target releases.

    In case of identical target releases too, drop events with lower IDs.
    """
    events_by_input = defaultdict(list)  # {(release, input packages): [event]}
    for event in events:
        input_packages_str = _packages_to_str(event.in_pkgs)
        events_by_input[(event.from_release, input_packages_str)].append(event)
    for input_events in events_by_input.values():
        if len(input_events) > 1:
            input_events.sort(key=lambda e: (e.to_release, e.id))
            api.current_logger().debug('Conflicting events with same input packages and initial release: #' +
                                       ', #'.join(str(e.id) for e in input_events))
            for event in input_events[:-1]:
                api.current_logger().debug('Dropping event #{}'.format(event.id))
                events.remove(event)


def process_events(releases, events, installed_pkgs):
    """
    Process PES events to get lists of pkgs to keep, to install and to remove.

    :param releases: List of tuples representing ordered releases in format (major, minor)
    :param events: List of Event tuples, not including those events with their "input" packages not installed
    :param installed_pkgs: Set of tuples holding names and module streams of installed Red Hat-signed packages
    :return: A dict with three dicts holding pkgs to keep, to install and to remove
    """
    # items in subdicts are Package tuples, just represented differently to allow efficient indexing
    # keys of subdicts are (<name>, <modulestream>), where <modulestream> can be (<module>, <stream>) or None
    # values of subdicts are <repository>
    tasks = {t: {} for t in Task}  # noqa: E1133; pylint: disable=not-an-iterable

    for release in releases:
        current = {t: {} for t in Task}  # noqa: E1133; pylint: disable=not-an-iterable
        release_events = [e for e in events if e.to_release == release]
        api.current_logger().debug('---- Processing {n} eligible events for release {r}'.format(
            n=len(release_events), r=release))

        for event in release_events:
            if is_event_relevant(event, installed_pkgs, tasks):
                if event.action in [Action.DEPRECATED, Action.PRESENT]:
                    # Keep these packages to make sure the repo they're in on the target system 8/9 gets enabled
                    add_packages_to_tasks(current, event.in_pkgs, Task.KEEP)

                if event.action == Action.MOVED:
                    # Keep these packages to make sure the repo they're in on the target system gets enabled
                    # We don't care about the "in_pkgs" as it contains always just one pkg - the same as the "out" pkg
                    add_packages_to_tasks(current, event.out_pkgs, Task.KEEP)

                if event.action in [Action.SPLIT, Action.MERGED, Action.RENAMED, Action.REPLACED]:
                    non_installed_out_pkgs = filter_out_installed_pkgs(event.out_pkgs, installed_pkgs)
                    add_packages_to_tasks(current, non_installed_out_pkgs, Task.INSTALL)
                    # Keep already installed "out" pkgs to ensure the repo they're in on the target system gets enabled
                    installed_out_pkgs = get_installed_event_pkgs(event.out_pkgs, installed_pkgs)
                    add_packages_to_tasks(current, installed_out_pkgs, Task.KEEP)

                    if event.action in [Action.SPLIT, Action.MERGED]:
                        # Remove those source pkgs that are no longer on the target system
                        filtered_in_pkgs = get_installed_event_pkgs(event.in_pkgs, installed_pkgs)
                        in_pkgs_without_out_pkgs = filter_out_out_pkgs(filtered_in_pkgs, event.out_pkgs)
                        add_packages_to_tasks(current, in_pkgs_without_out_pkgs, Task.REMOVE)

                if event.action in [Action.RENAMED, Action.REPLACED, Action.REMOVED]:
                    add_packages_to_tasks(current, event.in_pkgs, Task.REMOVE)

        do_not_remove = set()
        for package in current[Task.REMOVE]:
            if package in tasks[Task.KEEP]:
                api.current_logger().warning(
                    '{p} :: {r} to be kept / currently removed - removing package'.format(
                        p=package[0], r=current[Task.REMOVE][package]))
                del tasks[Task.KEEP][package]
            elif package in tasks[Task.INSTALL]:
                api.current_logger().warning(
                    '{p} :: {r} to be installed / currently removed - ignoring tasks'.format(
                        p=package[0], r=current[Task.REMOVE][package]))
                del tasks[Task.INSTALL][package]
                do_not_remove.add(package)
        for package in do_not_remove:
            del current[Task.REMOVE][package]

        do_not_install = set()
        for package in current[Task.INSTALL]:
            if package in tasks[Task.REMOVE]:
                api.current_logger().warning(
                    '{p} :: {r} to be removed / currently installed - keeping package'.format(
                        p=package[0], r=current[Task.INSTALL][package]))
                current[Task.KEEP][package] = current[Task.INSTALL][package]
                del tasks[Task.REMOVE][package]
                do_not_install.add(package)
        for package in do_not_install:
            del current[Task.INSTALL][package]

        for package in current[Task.KEEP]:
            if package in tasks[Task.REMOVE]:
                api.current_logger().warning(
                    '{p} :: {r} to be removed / currently kept - keeping package'.format(
                        p=package[0], r=current[Task.KEEP][package]))
                del tasks[Task.REMOVE][package]

        for key in Task:  # noqa: E1133; pylint: disable=not-an-iterable
            for package in current[key]:
                if package in tasks[key]:
                    api.current_logger().warning(
                        '{p} :: {r} to be {v} TWICE - internal bug (not serious, continuing)'.format(
                            p=package[0], r=current[key][package], v=key.past()))
            tasks[key].update(current[key])

    map_repositories(tasks[Task.INSTALL])
    map_repositories(tasks[Task.KEEP])
    filter_out_pkgs_in_blacklisted_repos(tasks[Task.INSTALL])
    resolve_conflicting_requests(tasks)

    return tasks


def filter_out_installed_pkgs(event_out_pkgs, installed_pkgs):
    """Do not install those packages that are already installed."""
    return {p for p in event_out_pkgs if (p.name, p.modulestream) not in installed_pkgs}


def get_installed_event_pkgs(event_pkgs, installed_pkgs):
    """
    Get those event's "in" or "out" packages which are already installed.

    Even though we don't want to install the already installed pkgs, in order to be able to upgrade
    them to their target RHEL major version we need to know in which repos they are and enable such repos.
    """
    return {p for p in event_pkgs if (p.name, p.modulestream) in installed_pkgs}


def filter_out_out_pkgs(event_in_pkgs, event_out_pkgs):
    """
    In case of a Split or Merge PES events some of the "out" packages can be the same as the "in" packages.

    We don't want to remove those "in" packages that are among "out" packages. For example in case of a split of gdbm
    to gdbm and gdbm-libs, we would incorrectly mandate removing gdbm without this filter. But for example in case of
    a split of Cython to python2-Cython and python3-Cython, we will correctly mandate removing Cython.
    """
    out_pkgs_keys = {p.name for p in event_out_pkgs}
    return {p for p in event_in_pkgs if p.name not in out_pkgs_keys}


SKIPPED_PKGS_MSG = (
    'packages will be skipped because they are available only in '
    'target system repositories that are intentionally excluded from the '
    'list of repositories used during the upgrade. '
    'See the report message titled "Excluded target system repositories" '
    'for details.\nThe list of these packages:'
)


def filter_out_pkgs_in_blacklisted_repos(to_install):
    """
    Do not install packages that are available in blacklisted repositories

    No need to filter out the to_keep packages as the blacklisted repos won't get enabled - that is ensured in the
    setuptargetrepos actor. So even if they fall into the 'yum upgrade' bucket, they won't be available thus upgraded.
    """
    # FIXME The to_install contains just a limited subset of packages - those that are *not* currently installed and
    #   are to be installed. But we should also warn about the packages that *are* installed.
    blacklisted_pkg_repo_pairs = set()
    blacklisted_repos = get_repositories_blacklisted()
    for pkg, repo in to_install.items():
        if repo in blacklisted_repos:
            blacklisted_pkg_repo_pairs.add((pkg, repo))

    for pkg, _ in blacklisted_pkg_repo_pairs:
        del to_install[pkg]

    if blacklisted_pkg_repo_pairs:
        report_skipped_packages(
            title='Packages available in excluded repositories will not be installed',
            message=SKIPPED_PKGS_MSG,
            package_repo_pairs=blacklisted_pkg_repo_pairs,
        )


def resolve_conflicting_requests(tasks):
    """
    Do not remove what is supposed to be kept or installed.

    PES events may give us conflicting requests - to both install/keep and remove a pkg.
    Example of two real-world PES events resulting in a conflict:
      PES event 1: sip-devel  SPLIT INTO   python3-sip-devel, sip
      PES event 2: sip        SPLIT INTO   python3-pyqt5-sip, python3-sip
        -> without this function, sip would reside in both [Task.KEEP] and [Task.REMOVE], causing a dnf conflict
    """
    pkgs_in_conflict = set()
    for pkg in list(tasks[Task.INSTALL].keys()) + list(tasks[Task.KEEP].keys()):
        if pkg in tasks[Task.REMOVE]:
            pkgs_in_conflict.add(pkg)
            del tasks[Task.REMOVE][pkg]

    if pkgs_in_conflict:
        api.current_logger().debug('The following packages were marked to be kept/installed and removed at the same'
                                   ' time. Leapp will upgrade them.\n{}'.format(
                                       '\n'.join(sorted(pkg[0] for pkg in pkgs_in_conflict))))


def get_repositories_blacklisted():
    """Consume message and return a set of blacklisted repositories"""
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


def map_repositories(packages):
    """Map repositories from PES data to RHSM repository id"""
    repositories_mapping = _get_repositories_mapping(set(packages.values()))
    pkg_with_repo_without_mapping = set()
    for pkg, repo in packages.items():
        if repo not in repositories_mapping:
            pkg_with_repo_without_mapping.add((pkg, repo))
            continue

        packages[pkg] = repositories_mapping[repo]

    for pkg, _ in pkg_with_repo_without_mapping:
        del packages[pkg]

    if pkg_with_repo_without_mapping:
        report_skipped_packages(
            title='Packages from unknown repositories may not be installed',
            message='packages may not be installed or upgraded due to repositories unknown to leapp:',
            package_repo_pairs=pkg_with_repo_without_mapping,
            remediation=(
                "Please file a bug in http://bugzilla.redhat.com/ for leapp-repository component of "
                "the Red Hat Enterprise Linux product."
            ),
        )


def report_skipped_packages(title, message, package_repo_pairs, remediation=None):
    """Generate report message about skipped packages"""
    package_repo_pairs = sorted(package_repo_pairs)
    summary = '{} {}\n{}'.format(
        len(package_repo_pairs), message, '\n'.join(
            [
                '- {pkg}{ms} (repoid: {repo})'.format(pkg=pkg[0], repo=repo,
                                                      ms=(' [{}:{}]'.format(*pkg[1]) if pkg[1] else ''))
                for pkg, repo in package_repo_pairs
            ]
        )
    )
    report_content = [
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.REPOSITORY]),
    ]
    if remediation:
        report_content += [reporting.Remediation(hint=remediation)]
    report_content += [reporting.RelatedResource('package', p[0]) for p, _ in package_repo_pairs]
    reporting.create_report(report_content)
    if is_verbose():
        api.current_logger().info(summary)


def add_output_pkgs_to_transaction_conf(transaction_configuration, events):
    """
    Filter out those PES events that conflict with the higher priority transaction configuration files.

    Output packages from an event are added to packages for removal only if all input packages are already there.

    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    :param events: List of Event tuples, where each event contains event type and input/output pkgs
    """
    message = 'The following target system packages will not be installed:\n'

    for event in events:
        if event.action in (Action.SPLIT, Action.MERGED, Action.REPLACED, Action.RENAMED):
            if all([pkg.name in transaction_configuration.to_remove for pkg in event.in_pkgs]):
                transaction_configuration.to_remove.extend(pkg.name for pkg in event.out_pkgs)
                message += (
                    '- {outs}\n - Reason: {ins} being {action} {to_or_by} {outs} {is_or_are} mentioned in the'
                    ' transaction configuration file /etc/leapp/transaction/to_remove\n'.format(
                        outs=', '.join(p.name for p in event.out_pkgs),
                        ins=', '.join(p.name for p in event.in_pkgs),
                        action=event.action.name.lower(),
                        to_or_by='by' if event.action == 'Replaced' else 'to',
                        is_or_are='is' if len(event.in_pkgs) == 1 else 'are'
                    )
                )

    api.current_logger().debug(message)


def filter_out_transaction_conf_pkgs(tasks, transaction_configuration):
    """
    Filter out those PES events conflicting with the higher priority transaction configuration files.

    :param tasks: A dict with three dicts holding pkgs to keep, to install and to remove
    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and REMOVE based
                                      on the user configuration files
    """
    do_not_keep = [p for p in tasks[Task.KEEP] if p[0] in transaction_configuration.to_remove]
    do_not_install = [p for p in tasks[Task.INSTALL] if p[0] in transaction_configuration.to_remove]
    do_not_remove = [p for p in tasks[Task.REMOVE] if p[0] in transaction_configuration.to_install
                     or p[0] in transaction_configuration.to_keep]

    for pkg in do_not_keep:
        # Removing a package from the to_keep dict may cause that some repositories won't get enabled
        tasks[Task.KEEP].pop(pkg)

    if do_not_install:
        for pkg in do_not_install:
            tasks[Task.INSTALL].pop(pkg)
        api.current_logger().debug('The following packages will not be installed because of the'
                                   ' /etc/leapp/transaction/to_remove transaction configuration file:'
                                   '\n- ' + '\n- '.join(p[0] for p in sorted(do_not_install)))
    if do_not_remove:
        for pkg in do_not_remove:
            tasks[Task.REMOVE].pop(pkg)
        api.current_logger().debug('The following packages will not be removed because of the to_keep and to_install'
                                   ' transaction configuration files in /etc/leapp/transaction/:'
                                   '\n- ' + '\n- '.join(p[0] for p in sorted(do_not_remove)))


def _get_enabled_modules():
    enabled_modules_msgs = api.consume(EnabledModules)
    enabled_modules_msg = next(enabled_modules_msgs, None)
    if list(enabled_modules_msgs):
        api.current_logger().warning('Unexpectedly received more than one EnabledModules message.')
    if not enabled_modules_msg:
        raise StopActorExecutionError('Cannot parse PES data properly due to missing list of enabled modules',
                                      details={'Problem': 'Did not receive a message with enabled module '
                                                          'streams (EnabledModules)'})
    return enabled_modules_msg.modules


def produce_messages(tasks):
    # Type casting to list to be Py2&Py3 compatible as on Py3 keys() returns dict_keys(), not a list
    to_install_pkgs = sorted(tasks[Task.INSTALL].keys())
    to_remove_pkgs = sorted(tasks[Task.REMOVE].keys())
    to_enable_repos = sorted(set(tasks[Task.INSTALL].values()) | set(tasks[Task.KEEP].values()))

    if to_install_pkgs or to_remove_pkgs:
        enabled_modules = _get_enabled_modules()
        modules_to_enable = [Module(name=p[1][0], stream=p[1][1]) for p in to_install_pkgs if p[1]]
        modules_to_reset = enabled_modules
        to_install_pkg_names = [p[0] for p in to_install_pkgs]
        to_remove_pkg_names = [p[0] for p in to_remove_pkgs]

        api.produce(PESRpmTransactionTasks(to_install=to_install_pkg_names,
                                           to_remove=to_remove_pkg_names,
                                           modules_to_enable=modules_to_enable,
                                           modules_to_reset=modules_to_reset))

    if to_enable_repos:
        api.produce(RepositoriesSetupTasks(to_enable=to_enable_repos))
