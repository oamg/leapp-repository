import json
import os
from collections import namedtuple

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import (InstalledRedHatSignedRPM, PESRpmTransactionTasks,
                          RepositoriesSetupTasks, RpmTransactionTasks, RepositoriesBlacklisted)

# FIXME: this mapping is not complete and will need to be manually updated frequently
REPOSITORIES_MAPPING = {
    'rhel8-appstream': 'rhel-8-for-x86_64-appstream-rpms',
    'rhel8-baseos': 'rhel-8-for-x86_64-baseos-rpms'}

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
    to_install, to_remove = process_events(filtered_events, installed_pkgs)
    filter_out_transaction_conf_pkgs(to_install, to_remove, transaction_configuration)
    produce_messages(to_install, to_remove)


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
        reporting.report_generic(title=title, summary=summary, severity='high', flags=['inhibitor'])
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
    Process PES events to get lists of pkgs to install or to remove.

    Compare the "to install" list to the already installed pkgs to not mandate installation of what is already
    installed. Also, filter out installation of pkgs in blacklisted repos.

    :param events: List of Event tuples, not including those events with their "input" packages not installed
    :param installed_pkgs: Set of names of the installed Red Hat-signed packages
    :return: A tuple with two dicts {<pkg_name>: <repository>} - one with pkgs to install and one with pkgs to remove
    """
    # Dicts in format {<pkg_name>: <repository>}
    to_install = {}
    to_remove = {}

    for event in events:
        if event.action in ('Deprecated', 'Moved', 'Present'):
            # No need to mandate installation of these. If they are installed on the system, the default in the dnf
            # plugin is to add them to the "to upgrade" group, which is correct in this case.
            continue

        if event.action in ('Renamed', 'Replaced'):
            non_installed_out_pkgs = filter_out_installed_pkgs(event.out_pkgs, installed_pkgs)
            to_install.update(non_installed_out_pkgs)

        if event.action in ('Split', 'Merged'):
            non_installed_out_pkgs = filter_out_installed_pkgs(event.out_pkgs, installed_pkgs)
            to_install.update(non_installed_out_pkgs)
            in_pkgs_without_out_pkgs = filter_out_out_pkgs(event.in_pkgs, event.out_pkgs)
            to_remove.update(in_pkgs_without_out_pkgs)

        if event.action in ('Renamed', 'Replaced', 'Removed'):
            to_remove.update(event.in_pkgs)

    filter_out_pkgs_in_blacklisted_repos(to_install)
    map_repositories(to_install)

    return to_install, to_remove


def filter_out_installed_pkgs(event_out_pkgs, installed_pkgs):
    """Do not try to install those packages that are already installed."""
    return {k: v for k, v in event_out_pkgs.items() if k not in installed_pkgs}


def filter_out_out_pkgs(event_in_pkgs, event_out_pkgs):
    """
    In case of a Split or Merge PES events some of the "out" packages can be the same as the "in" packages.

    We don't want to remove those "in" packages that are among "out" packages. For example in case of a split of gdbm
    to gdbm and gdbm-libs, we would incorrectly mandate removing gdbm without this filter. But for example in case of
    a split of Cython to python2-Cython and python3-Cython, we will correctly mandate removing Cython.
    """
    return {k: v for k, v in event_in_pkgs.items() if k not in event_out_pkgs.keys()}


def filter_out_pkgs_in_blacklisted_repos(to_install):
    """Do not install packages that are available in blacklisted repositories"""
    # FIXME The to_install contains just a limited subset of packages - those that are *not* currently installed and
    # are to be installed. But we should also warn about the packages that *are* installed.
    blacklisted_pkgs = set()
    for pkg, repo in to_install.items():
        if repo in get_repositories_blacklisted():
            blacklisted_pkgs.add(pkg)
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


def map_repositories(to_install):
    """Map repositories from PES data to RHSM repository id"""
    repo_not_mapped_pkgs = set()
    for pkg, repo in to_install.items():
        if repo not in REPOSITORIES_MAPPING.keys():
            repo_not_mapped_pkgs.add(pkg)
            del to_install[pkg]
            continue

        to_install[pkg] = REPOSITORIES_MAPPING[repo]

    if repo_not_mapped_pkgs:
        report_skipped_packages('packages will not be installed due to not mapped repositories:',
                                repo_not_mapped_pkgs)


def report_skipped_packages(message, packages):
    """Generate report message about skipped packages"""
    title = 'Packages will not be installed'
    summary = '{} {}\n{}'.format(len(packages), message, '\n'.join(['- ' + p for p in packages]))
    reporting.report_generic(title=title, summary=summary, severity='high')
    if is_verbose():
        api.show_message(summary)


def add_output_pkgs_to_transaction_conf(transaction_configuration, events):
    """
    Add more packages for removal to transaction configuration if they can be derived as outputs of PES events.

    Output packages from an event are added to packages for removal only if all input packages are already there.

    :param events: List of Event tuples, where each event contains event type and input/output pkgs
    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    """
    message = 'Marking packages for removal as a result of events:\n'

    for event in events:
        if event.action in ('Split', 'Merged', 'Replaced', 'Renamed'):
            if all([pkg in transaction_configuration.to_remove for pkg in event.in_pkgs]):
                transaction_configuration.to_remove.extend(event.out_pkgs)
                message += '- [{}] {} -> {}\n'.format(event.action,
                                                      ', '.join(event.in_pkgs.keys()),
                                                      ', '.join(event.out_pkgs.keys()))

    api.current_logger().debug(message)


def filter_out_transaction_conf_pkgs(to_install, to_remove, transaction_configuration):
    """
    Filter out those PES events that conflict with the higher priority transaction configuration files.

    :param to_install: A dict {<pkg_name>: <repository>} with pkgs to install based on PES data
    :param to_remove: A dict {<pkg_name>: <repository>} with pkgs to remove based on PES data
    :param transaction_configuration: RpmTransactionTasks model instance with pkgs to install, keep and remove based
                                      on the user configuration files
    """
    # The two lists below are for debug message purposes only
    pes_based_pkgs_not_to_be_installed = []
    pes_based_pkgs_not_to_be_removed = []

    for pes_based_pkg_to_install in to_install.keys():
        if pes_based_pkg_to_install in transaction_configuration.to_remove:
            to_install.pop(pes_based_pkg_to_install)
            pes_based_pkgs_not_to_be_installed.append(pes_based_pkg_to_install)
    for pes_based_pkg_to_remove in to_remove.keys():
        if pes_based_pkg_to_remove in (transaction_configuration.to_install + transaction_configuration.to_keep):
            to_remove.pop(pes_based_pkg_to_remove)
            pes_based_pkgs_not_to_be_removed.append(pes_based_pkg_to_remove)

    if pes_based_pkgs_not_to_be_installed:
        api.current_logger().debug('The following packages will not be installed because of the'
                                   ' /etc/leapp/transaction/to_remove transaction configuration file:'
                                   '\n- ' + '\n- '.join(pes_based_pkgs_not_to_be_installed))
    if pes_based_pkgs_not_to_be_removed:
        api.current_logger().debug('The following packages will not be removed because of the to_keep and to_install'
                                   ' transaction configuration files in /etc/leapp/transaction/:'
                                   '\n- ' + '\n- '.join(pes_based_pkgs_not_to_be_removed))


def produce_messages(to_install, to_remove):
    to_install_pkgs = set(to_install.keys())
    to_remove_pkgs = set(to_remove.keys())
    to_enable_repos = set(to_install.values())

    if to_install_pkgs or to_remove_pkgs:
        api.produce(PESRpmTransactionTasks(to_install=list(to_install_pkgs),
                                           to_remove=list(to_remove_pkgs)))

    if to_enable_repos:
        api.produce(RepositoriesSetupTasks(to_enable=list(to_enable_repos)))
