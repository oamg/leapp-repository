import json
import os
from collections import namedtuple
from enum import IntEnum

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp import reporting
from leapp.libraries.common.config import architecture, version
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import (InstalledRedHatSignedRPM, PESRpmTransactionTasks, RepositoriesMap,
                          RepositoriesSetupTasks, RpmTransactionTasks, RepositoriesBlacklisted)


Event = namedtuple('Event', ['action',        # A string representing an event type (see EVENT_TYPES)
                             'in_pkgs',       # A dictionary with packages in format {<pkg_name>: <repository>}
                             'out_pkgs',      # A dictionary with packages in format {<pkg_name>: <repository>}
                             'from_release',  # A tuple representing a release in format (major, minor)
                             'to_release',    # A tuple representing a release in format (major, minor)
                             'architectures'  # A list of strings representing architectures
                             ])

EVENT_TYPES = ('Present', 'Removed', 'Deprecated', 'Replaced', 'Split', 'Merged', 'Moved', 'Renamed')


class Task(IntEnum):
    keep = 0
    install = 1
    remove = 2

    def past(self):
        return ['kept', 'installed', 'removed'][self]


def pes_events_scanner(pes_json_filepath):
    """Entrypoint to the library"""
    installed_pkgs = get_installed_pkgs()
    transaction_configuration = get_transaction_configuration()
    arch = api.current_actor().configuration.architecture
    events = get_events(pes_json_filepath)
    releases = get_releases(events)
    target = version._version_to_tuple(api.current_actor().configuration.version.target)

    filtered_releases = filter_releases_by_target(releases, target)
    filtered_events = filter_events_by_releases(events, filtered_releases)
    arch_events = filter_events_by_architecture(filtered_events, arch)

    add_output_pkgs_to_transaction_conf(transaction_configuration, arch_events)
    tasks = process_events(filtered_releases, arch_events, installed_pkgs)
    filter_out_transaction_conf_pkgs(tasks, transaction_configuration)
    produce_messages(tasks)


def get_installed_pkgs():
    """
    Get installed Red Hat-signed packages.

    :return: Set of names of the installed Red Hat-signed packages
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
    installed_pkgs.update([pkg.name for pkg in installed_rh_signed_rpm_msg.items])
    return installed_pkgs


def _get_repositories_mapping():
    """
    Get all repositories mapped from repomap file and map repositories id with respective names.

    :return: Dictionary with all repositories mapped.
    """
    repositories_mapping = {}

    repositories_map_msgs = api.consume(RepositoriesMap)
    repositories_map_msg = next(repositories_map_msgs, None)
    if list(repositories_map_msgs):
        api.current_logger().warning('Unexpectedly received more than one RepositoriesMap message.')
    if not repositories_map_msg:
        raise StopActorExecutionError(
            'Cannot parse RepositoriesMap data properly',
            details={'Problem': 'Did not receive a message with mapped repositories'}
        )

    for repository in repositories_map_msg.repositories:
        if repository.arch == api.current_actor().configuration.architecture:
            repositories_mapping[repository.to_pes_repo] = repository.to_repoid

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


def filter_releases_by_target(releases, target):
    return [r for r in releases if version.matches_version(
        ['<= {}.{}'.format(*target)], '{}.{}'.format(*r))]


def get_events(pes_events_filepath):
    """
    Get all the events from the source JSON file exported from PES.

    :return: List of Event tuples, where each event contains event type and input/output pkgs
    """
    try:
        return parse_pes_events_file(pes_events_filepath)
    except (ValueError, KeyError):
        title = 'Missing/Invalid PES data file ({})'.format(pes_events_filepath)
        summary = 'Read documentation at: https://access.redhat.com/articles/3664871 for more information ' \
            'about how to retrieve the files'
        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SANITY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.RelatedResource('file', pes_events_filepath)
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


def parse_pes_events_file(path):
    """
    Parse JSON file returning PES events

    :return: List of Event tuples, where each event contains event type and input/output pkgs
    """
    if path is None or not os.path.isfile(path):
        raise ValueError('File {} not found'.format(path))
    with open(path) as f:
        data = json.load(f)

        if not isinstance(data, dict) or not data.get('packageinfo'):
            raise ValueError('Found PES data with invalid structure')

        return [parse_entry(entry) for entry in data['packageinfo']]


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

    action = parse_action(entry['action'])
    in_pkgs = parse_packageset(entry.get('in_packageset') or {})
    out_pkgs = parse_packageset(entry.get('out_packageset') or {})
    from_release = parse_release(entry.get('initial_release') or {})
    to_release = parse_release(entry.get('release') or {})
    architectures = parse_architectures(entry.get('architectures') or [])

    return Event(action, in_pkgs, out_pkgs, from_release, to_release, architectures)


def parse_action(action_id):
    """Get event type name based on PES event's action id"""
    if action_id < 0 or action_id >= len(EVENT_TYPES):
        raise ValueError('Found event with invalid action ID: {}'. format(action_id))

    return EVENT_TYPES[action_id]


def parse_packageset(packageset):
    """
    Get "input" or "output" packages and their repositories from each PES event.

    :return: A dictionary with packages in format {<pkg_name>: <repository>}
    """
    return {p['name']: p['repository'].lower() for p in packageset.get('package', [])}


def parse_release(release):
    return (release['major_version'], release['minor_version']) if release else (0, 0)


def parse_architectures(architectures):
    for arch in architectures:
        if arch not in architecture.ARCH_ACCEPTED:
            raise ValueError('Found event with invalid architecture: {}'. format(arch))
    return architectures


def is_event_relevant(event, installed_pkgs, tasks):
    """Determine if event is applicable given the installed packages and tasks planned so far."""
    for package in event.in_pkgs.keys():
        if package in tasks[Task.remove] and event.action != 'Present':
            return False
        if package not in installed_pkgs and package not in tasks[Task.install]:
            return False
    return True


def add_packages_to_tasks(tasks, packages, task_type):
    if packages:
        api.current_logger().debug('{v:7} {p}'.format(v=task_type.name.upper(), p=', '.join(packages)))
        tasks[task_type].update(packages)


def process_events(releases, events, installed_pkgs):
    """
    Process PES events to get lists of pkgs to keep, to install and to remove.

    :param releases: List of tuples representing ordered releases in format (major, minor)
    :param events: List of Event tuples, not including those events with their "input" packages not installed
    :param installed_pkgs: Set of names of the installed Red Hat-signed packages
    :return: A dict with three dicts holding pkgs to keep, to install and to remove
    """

    # subdicts in format {<pkg_name>: <repository>}
    tasks = {t: {} for t in Task}  # noqa: E1133; pylint: disable=not-an-iterable

    for release in releases:
        current = {t: {} for t in Task}  # noqa: E1133; pylint: disable=not-an-iterable
        release_events = [e for e in events if e.to_release == release]
        api.current_logger().debug('---- Processing {n} eligible events for release {r}'.format(
            n=len(release_events), r=release))

        for event in release_events:
            if is_event_relevant(event, installed_pkgs, tasks):
                if event.action in ('Deprecated', 'Present'):
                    # Keep these packages to make sure the repo they're in on RHEL 8 gets enabled
                    add_packages_to_tasks(current, event.in_pkgs, Task.keep)

                if event.action == 'Moved':
                    # Keep these packages to make sure the repo they're in on RHEL 8 gets enabled
                    # We don't care about the "in_pkgs" as it contains always just one pkg - the same as the "out" pkg
                    add_packages_to_tasks(current, event.out_pkgs, Task.keep)

                if event.action in ('Split', 'Merged', 'Renamed', 'Replaced'):
                    non_installed_out_pkgs = filter_out_installed_pkgs(event.out_pkgs, installed_pkgs)
                    add_packages_to_tasks(current, non_installed_out_pkgs, Task.install)
                    # Keep already installed "out" pkgs to ensure the repo they're in on RHEL 8 gets enabled
                    installed_out_pkgs = get_installed_event_pkgs(event.out_pkgs, installed_pkgs)
                    add_packages_to_tasks(current, installed_out_pkgs, Task.keep)

                    if event.action in ('Split', 'Merged'):
                        # Remove those RHEL 7 pkgs that are no longer on RHEL 8
                        in_pkgs_without_out_pkgs = filter_out_out_pkgs(event.in_pkgs, event.out_pkgs)
                        add_packages_to_tasks(current, in_pkgs_without_out_pkgs, Task.remove)

                if event.action in ('Renamed', 'Replaced', 'Removed'):
                    add_packages_to_tasks(current, event.in_pkgs, Task.remove)

        do_not_remove = set()
        for package in current[Task.remove]:
            if package in tasks[Task.keep]:
                api.current_logger().warning(
                    '{p} :: {r} to be kept / currently removed - removing package'.format(
                        p=package, r=current[Task.remove][package]))
                del tasks[Task.keep][package]
            elif package in tasks[Task.install]:
                api.current_logger().warning(
                    '{p} :: {r} to be installed / currently removed - ignoring tasks'.format(
                        p=package, r=current[Task.remove][package]))
                del tasks[Task.install][package]
                do_not_remove.add(package)
        for package in do_not_remove:
            del current[Task.remove][package]

        for package in current[Task.install]:
            if package in tasks[Task.remove]:
                api.current_logger().warning(
                    '{p} :: {r} to be removed / currently installed - keeping package'.format(
                        p=package, r=current[Task.install][package]))
                current[Task.keep][package] = current[Task.install][package]
                del tasks[Task.remove][package]
                del current[Task.install][package]

        for package in current[Task.keep]:
            if package in tasks[Task.remove]:
                api.current_logger().warning(
                    '{p} :: {r} to be removed / currently kept - keeping package'.format(
                        p=package, r=current[Task.keep][package]))
                del tasks[Task.remove][package]

        for key in Task:  # noqa: E1133; pylint: disable=not-an-iterable
            for package in current[key]:
                if package in tasks[key]:
                    api.current_logger().warning(
                        '{p} :: {r} to be {v} TWICE - internal bug (not serious, continuing)'.format(
                            p=package, r=current[key][package], v=key.past()))
            tasks[key].update(current[key])

    map_repositories(tasks[Task.install])
    map_repositories(tasks[Task.keep])
    filter_out_pkgs_in_blacklisted_repos(tasks[Task.install])
    resolve_conflicting_requests(tasks)

    return tasks


def filter_out_installed_pkgs(event_out_pkgs, installed_pkgs):
    """Do not install those packages that are already installed."""
    return {k: v for k, v in event_out_pkgs.items() if k not in installed_pkgs}


def get_installed_event_pkgs(event_pkgs, installed_pkgs):
    """
    Get those event's "in" or "out" packages which are already installed.

    Even though we don't want to install the already installed pkgs, to be able to upgrade them to their RHEL 8 version
    we need to know in which repos they are and enable such repos.
    """
    return {k: v for k, v in event_pkgs.items() if k in installed_pkgs}


def filter_out_out_pkgs(event_in_pkgs, event_out_pkgs):
    """
    In case of a Split or Merge PES events some of the "out" packages can be the same as the "in" packages.

    We don't want to remove those "in" packages that are among "out" packages. For example in case of a split of gdbm
    to gdbm and gdbm-libs, we would incorrectly mandate removing gdbm without this filter. But for example in case of
    a split of Cython to python2-Cython and python3-Cython, we will correctly mandate removing Cython.
    """
    return {k: v for k, v in event_in_pkgs.items() if k not in event_out_pkgs}


def filter_out_pkgs_in_blacklisted_repos(to_install):
    """
    Do not install packages that are available in blacklisted repositories

    No need to filter out the to_keep packages as the blacklisted repos won't get enabled - that is ensured in the
    setuptargetrepos actor. So even if they fall into the 'yum upgrade' bucket, they won't be available thus upgraded.
    """
    # FIXME The to_install contains just a limited subset of packages - those that are *not* currently installed and
    # are to be installed. But we should also warn about the packages that *are* installed.
    blacklisted_pkgs = set()
    blacklisted_repos = get_repositories_blacklisted()
    for pkg, repo in to_install.items():
        if repo in blacklisted_repos:
            blacklisted_pkgs.add(pkg)

    for pkg in blacklisted_pkgs:
        del to_install[pkg]

    if blacklisted_pkgs:
        report_skipped_packages('packages will not be installed due to blacklisted repositories:',
                                blacklisted_pkgs)


def resolve_conflicting_requests(tasks):
    """
    Do not remove what is supposed to be kept or installed.

    PES events may give us conflicting requests - to both install/keep and remove a pkg.
    Example of two real-world PES events resulting in a conflict:
      PES event 1: sip-devel  SPLIT INTO   python3-sip-devel, sip
      PES event 2: sip        SPLIT INTO   python3-pyqt5-sip, python3-sip
        -> without this function, sip would reside in both [Task.keep] and [Task.remove], causing a dnf conflict
    """
    pkgs_in_conflict = set()
    for pkg in list(tasks[Task.install].keys()) + list(tasks[Task.keep].keys()):
        if pkg in tasks[Task.remove]:
            pkgs_in_conflict.add(pkg)
            del tasks[Task.remove][pkg]

    if pkgs_in_conflict:
        api.current_logger().debug('The following packages were marked to be kept/installed and removed at the same'
                                   ' time. Leapp will upgrade them.\n{}'.format('\n'.join(sorted(pkgs_in_conflict))))


def get_repositories_blacklisted():
    """Consume message and return a set of blacklisted repositories"""
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


def map_repositories(packages):
    """Map repositories from PES data to RHSM repository id"""
    repositories_mapping = _get_repositories_mapping()
    repo_without_mapping = set()
    for pkg, repo in packages.items():
        if repo not in repositories_mapping:
            repo_without_mapping.add(pkg)
            continue

        packages[pkg] = repositories_mapping[repo]

    for pkg in repo_without_mapping:
        del packages[pkg]

    if repo_without_mapping:
        report_skipped_packages('packages will not be installed or upgraded due to repositories unknown to leapp:',
                                repo_without_mapping)


def report_skipped_packages(message, packages):
    """Generate report message about skipped packages"""
    packages = sorted(packages)
    title = 'Packages will not be installed'
    summary = '{} {}\n{}'.format(len(packages), message, '\n'.join(['- ' + p for p in packages]))
    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.REPOSITORY]),
    ] + [reporting.RelatedResource('package', p) for p in packages])
    if is_verbose():
        api.show_message(summary)


def add_output_pkgs_to_transaction_conf(transaction_configuration, events):
    """
    Add more packages for removal to transaction configuration if they can be derived as outputs of PES events.

    Output packages from an event are added to packages for removal only if all input packages are already there.

    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    :param events: List of Event tuples, where each event contains event type and input/output pkgs
    """
    message = 'Marking packages for removal:\n'

    for event in events:
        if event.action in ('Split', 'Merged', 'Replaced', 'Renamed'):
            if all([pkg in transaction_configuration.to_remove for pkg in event.in_pkgs]):
                transaction_configuration.to_remove.extend(event.out_pkgs)
                message += '- [{action}] {ins} -> {outs}\n'.format(
                    action=event.action,
                    ins=', '.join(sorted(event.in_pkgs.keys())),
                    outs=', '.join(sorted(event.out_pkgs.keys()))
                )

    api.current_logger().debug(message)


def filter_out_transaction_conf_pkgs(tasks, transaction_configuration):
    """
    Filter out those PES events conflicting with the higher priority transaction configuration files.

    :param tasks: A dict with three dicts holding pkgs to keep, to install and to remove
    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    """
    do_not_keep = [p for p in tasks[Task.keep] if p in transaction_configuration.to_remove]
    do_not_install = [p for p in tasks[Task.install] if p in transaction_configuration.to_remove]
    do_not_remove = [p for p in tasks[Task.remove] if p in transaction_configuration.to_install
                     or p in transaction_configuration.to_keep]

    for pkg in do_not_keep:
        # Removing a package from the to_keep dict may cause that some repositories won't get enabled
        tasks[Task.keep].pop(pkg)

    if do_not_install:
        for pkg in do_not_install:
            tasks[Task.install].pop(pkg)
        api.current_logger().debug('The following packages will not be installed because of the'
                                   ' /etc/leapp/transaction/to_remove transaction configuration file:'
                                   '\n- ' + '\n- '.join(sorted(do_not_install)))
    if do_not_remove:
        for pkg in do_not_remove:
            tasks[Task.remove].pop(pkg)
        api.current_logger().debug('The following packages will not be removed because of the to_keep and to_install'
                                   ' transaction configuration files in /etc/leapp/transaction/:'
                                   '\n- ' + '\n- '.join(sorted(do_not_remove)))


def produce_messages(tasks):
    # Type casting to list to be Py2&Py3 compatible as on Py3 keys() returns dict_keys(), not a list
    to_install_pkgs = sorted(tasks[Task.install].keys())
    to_remove_pkgs = sorted(tasks[Task.remove].keys())
    to_enable_repos = sorted(set(tasks[Task.install].values() + tasks[Task.keep].values()))

    if to_install_pkgs or to_remove_pkgs:
        api.produce(PESRpmTransactionTasks(to_install=to_install_pkgs,
                                           to_remove=to_remove_pkgs))

    if to_enable_repos:
        api.produce(RepositoriesSetupTasks(to_enable=to_enable_repos))
