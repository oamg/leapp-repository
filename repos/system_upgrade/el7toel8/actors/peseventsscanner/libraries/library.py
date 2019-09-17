import json
import os
from collections import namedtuple

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import (InstalledRedHatSignedRPM, PESRpmTransactionTasks,
                          RepositoriesSetupTasks, RpmTransactionTasks, RepositoriesBlacklisted)

# FIXME: this mapping is not complete and will need to be manually updated frequently
REPOSITORIES_MAPPING = {
    'rhel8-appstream': 'rhel-8-for-x86_64-appstream-rpms',
    'rhel8-baseos': 'rhel-8-for-x86_64-baseos-rpms',
    'rhel8-crb': 'codeready-builder-for-rhel-8-x86_64-rpms',
    'rhel8-supplementary': 'rhel-8-for-x86_64-supplementary-rpms'}

Event = namedtuple('Event', ['action',   # A string representing an event type (see EVENT_TYPES)
                             'in_pkgs',  # A dictionary with packages in format {<pkg_name>: <repository>}
                             'out_pkgs'  # A dictionary with packages in format {<pkg_name>: <repository>}
                             ])

EVENT_TYPES = ('Present', 'Removed', 'Deprecated', 'Replaced', 'Split', 'Merged', 'Moved', 'Renamed')


def pes_events_scanner(pes_json_filepath):
    """Entrypoint to the library"""
    installed_pkgs = get_installed_pkgs()
    transaction_configuration = get_transaction_configuration()
    events = get_events(pes_json_filepath)
    add_output_pkgs_to_transaction_conf(transaction_configuration, events)
    filtered_events = get_events_for_installed_pkgs_only(events, installed_pkgs)
    tasks = process_events(filtered_events, installed_pkgs)
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
                      }
                      'out_packageset': {  # 'out_packageset' can be None
                          'set_id': 21,
                          'package': [
                              {
                                  'name': 'espeak-ng',
                                  'repository': 'rhel8-AppStream'
                              }
                          ]
                      },
                  }
    """
    action = parse_action(entry['action'])
    in_pkgs = parse_packageset(entry.get('in_packageset') or {})
    out_pkgs = parse_packageset(entry.get('out_packageset') or {})

    return Event(action, in_pkgs, out_pkgs)


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


def get_events_for_installed_pkgs_only(events, installed_rh_pkgs):
    """
    Get those PES events that have at least one of the event's "input" packages installed and signed by Red Hat.

    :param events: List of Event tuples, where each event contains event type and input/output pkgs
    :param installed_rh_pkgs: Set of names of the installed Red Hat-signed packages
    :return: List of Event tuples, not including those events whose input packages are not installed
    """

    filtered = []
    for event in events:
        if is_at_least_one_event_input_pkg_installed(installed_rh_pkgs, event.in_pkgs):
            filtered.append(event)

    return filtered


def is_at_least_one_event_input_pkg_installed(installed_rh_pkgs, event_in_pkgs):
    return installed_rh_pkgs.intersection(set(event_in_pkgs.keys()))


def process_events(events, installed_pkgs):
    """
    Process PES events to get lists of pkgs to keep, to install and to remove.

    :param events: List of Event tuples, not including those events with their "input" packages not installed
    :param installed_pkgs: Set of names of the installed Red Hat-signed packages
    :return: A dict with three dicts holding pkgs to keep, to install and to remove
    """

    tasks = {  # Contains dicts in format {<pkg_name>: <repository>}
        'to_keep': {},
        'to_install': {},
        'to_remove': {}}

    for event in events:
        if event.action in ('Deprecated', 'Present'):
            # Add these packages to to_keep to make sure the repo they're in on RHEL 8 gets enabled
            tasks['to_keep'].update(event.in_pkgs)

        if event.action == 'Moved':
            # Add these packages to to_keep to make sure the repo they're in on RHEL 8 gets enabled
            # We don't care about the "in_pkgs" as it contains always just one pkg - the same as the "out" pkg
            tasks['to_keep'].update(event.out_pkgs)

        if event.action in ('Split', 'Merged', 'Renamed', 'Replaced'):
            non_installed_out_pkgs = filter_out_installed_pkgs(event.out_pkgs, installed_pkgs)
            tasks['to_install'].update(non_installed_out_pkgs)
            # Add the already installed "out" pkgs to to_keep to make sure the repo they're in on RHEL 8 gets enabled
            installed_out_pkgs = get_installed_out_pkgs(event.out_pkgs, installed_pkgs)
            tasks['to_keep'].update(installed_out_pkgs)
            if event.action in ('Split', 'Merged'):
                # Uninstall those RHEL 7 pkgs that are no longer on RHEL 8
                in_pkgs_without_out_pkgs = filter_out_out_pkgs(event.in_pkgs, event.out_pkgs)
                tasks['to_remove'].update(in_pkgs_without_out_pkgs)

        if event.action in ('Renamed', 'Replaced', 'Removed'):
            # Uninstall those RHEL 7 pkgs that are no longer on RHEL 8
            tasks['to_remove'].update(event.in_pkgs)

    map_repositories(tasks['to_install'])
    map_repositories(tasks['to_keep'])
    filter_out_pkgs_in_blacklisted_repos(tasks['to_install'])

    return tasks


def filter_out_installed_pkgs(event_out_pkgs, installed_pkgs):
    """Do not install those packages that are already installed."""
    return {k: v for k, v in event_out_pkgs.items() if k not in installed_pkgs}


def get_installed_out_pkgs(event_out_pkgs, installed_pkgs):
    """
    Get those event's "out" packages which are already installed.

    Even though we don't want to install the already installed pkgs, to be able to upgrade them to their RHEL 8 version
    we need to know in which repos they are and enable such repos.
    """
    return {k: v for k, v in event_out_pkgs.items() if k in installed_pkgs}


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
    for pkg, repo in to_install.items():
        if repo in get_repositories_blacklisted():
            blacklisted_pkgs.add(pkg)

    for pkg in blacklisted_pkgs:
        del to_install[pkg]

    if blacklisted_pkgs:
        report_skipped_packages('packages will not be installed due to blacklisted repositories:',
                                blacklisted_pkgs)


def get_repositories_blacklisted():
    """Consume message and return a set of blacklisted repositories"""
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


def map_repositories(packages):
    """
    Map repositories from PES data to RHSM repository id

    :param packages: A dictionary in format {<pkg_name>: <repository>}
    """
    repo_without_mapping = set()
    for pkg, repo in packages.items():
        if repo not in REPOSITORIES_MAPPING:
            repo_without_mapping.add(pkg)
            continue

        packages[pkg] = REPOSITORIES_MAPPING[repo]

    for pkg in repo_without_mapping:
        del packages[pkg]

    if repo_without_mapping:
        report_skipped_packages('packages will not be installed or upgraded due to repositories unknown to leapp:',
                                repo_without_mapping)


def report_skipped_packages(message, packages):
    """Generate report message about skipped packages"""
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
                    ins=', '.join(event.in_pkgs.keys()),
                    outs=', '.join(event.out_pkgs.keys())
                )

    api.current_logger().debug(message)


def filter_out_transaction_conf_pkgs(tasks, transaction_configuration):
    """
    Filter out those PES events conflicting with the higher priority transaction configuration files.

    :param tasks: A dict with three dicts holding pkgs to keep, to install and to remove
    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    """
    pkgs_not_to_be_kept = []
    pkgs_not_to_be_installed = []
    pkgs_not_to_be_removed = []

    for pkg_to_keep in tasks['to_keep']:
        if pkg_to_keep in transaction_configuration.to_remove:
            pkgs_not_to_be_kept.append(pkg_to_keep)
    for pkg_to_install in tasks['to_install']:
        if pkg_to_install in transaction_configuration.to_remove:
            pkgs_not_to_be_installed.append(pkg_to_install)
    for pkg_to_remove in tasks['to_remove']:
        if pkg_to_remove in transaction_configuration.to_install + transaction_configuration.to_keep:
            pkgs_not_to_be_removed.append(pkg_to_remove)

    for pkg in pkgs_not_to_be_kept:
        # Removing a package from the to_keep dict may cause that some repositories won't get enabled
        tasks['to_keep'].pop(pkg)

    if pkgs_not_to_be_installed:
        for pkg in pkgs_not_to_be_installed:
            tasks['to_install'].pop(pkg)
        api.current_logger().debug('The following packages will not be installed because of the'
                                   ' /etc/leapp/transaction/to_remove transaction configuration file:'
                                   '\n- ' + '\n- '.join(pkgs_not_to_be_installed))
    if pkgs_not_to_be_removed:
        for pkg in pkgs_not_to_be_removed:
            tasks['to_remove'].pop(pkg)
        api.current_logger().debug('The following packages will not be removed because of the to_keep and to_install'
                                   ' transaction configuration files in /etc/leapp/transaction/:'
                                   '\n- ' + '\n- '.join(pkgs_not_to_be_removed))


def produce_messages(tasks):
    # Type casting to list to be Py2&Py3 compatible as on Py3 keys() returns dict_keys(), not a list
    to_install_pkgs = list(tasks['to_install'].keys())
    to_remove_pkgs = list(tasks['to_remove'].keys())
    to_enable_repos = list(set(tasks['to_install'].values() + tasks['to_keep'].values()))

    if to_install_pkgs or to_remove_pkgs:
        api.produce(PESRpmTransactionTasks(to_install=to_install_pkgs,
                                           to_remove=to_remove_pkgs))

    if to_enable_repos:
        api.produce(RepositoriesSetupTasks(to_enable=to_enable_repos))
