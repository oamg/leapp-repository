import json
import os
from collections import namedtuple

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.stdlib.config import is_verbose
from leapp.models import InstalledRedHatSignedRPM, RepositoriesBlacklisted, RepositoriesSetupTasks,\
    RpmTransactionTasks


# FIXME: this mapping is not complete and will need to be manually updated frequently
REPOSITORIES_MAPPING = {
    'rhel8-appstream': 'rhel-8-for-x86_64-appstream-htb-rpms',
    'rhel8-baseos': 'rhel-8-for-x86_64-baseos-htb-rpms'}


Event = namedtuple('Event', ['action', 'in_pkgs', 'out_pkgs'])


def parse_action(action_id):
    """ Get action label from PES event's action id """
    labels = ('Present', 'Removed', 'Deprecated', 'Replaced', 'Split', 'Merged', 'Moved', 'Renamed')

    if action_id < 0 or action_id >= len(labels):
        raise ValueError('Found event with invalid action ID: {}'. format(action_id))

    return labels[action_id]


def parse_packageset(packageset):
    """ Get packages and repositories data from PES event's package set """
    return {p['name']: p['repository'].lower() for p in packageset.get('package', [])}


def parse_entry(entry):
    """ Parse PES event data """
    action = parse_action(entry['action'])
    in_pkgs = parse_packageset(entry.get('in_packageset', {}) or {})
    out_pkgs = parse_packageset(entry.get('out_packageset', {}) or {})

    return Event(action, in_pkgs, out_pkgs)


def parse_file(path):
    """ Parse JSON file returning PES events """
    if path is None or not os.path.isfile(path):
        raise ValueError('File not found')
    with open(path) as f:
        data = json.load(f)

        if not isinstance(data, dict) or not data.get('packageinfo'):
            raise ValueError('Found PES data with invalid structure')

        return [parse_entry(entry) for entry in data['packageinfo']]


def filter_events(events):
    """ Filter PES events """
    installed_pkgs = set()
    for pkgs in api.consume(InstalledRedHatSignedRPM):
        installed_pkgs.update([pkg.name for pkg in pkgs.items])

    filtered = []
    for event in events:
        if not installed_pkgs.intersection(set(event.in_pkgs.keys())):
            continue

        filtered.append(event)

    return filtered


def report_skipped_packages(message, packages):
    """ Generate report about skipped packages """
    title = 'Packages will not be installed'
    summary = '{} {}\n{}'.format(len(packages), message, '\n'.join(['- ' + p for p in packages]))
    reporting.report_generic(title=title, summary=summary, severity='high')
    if is_verbose():
        api.show_message(summary)


def get_repositories_blacklisted():
    """ Consumes message and returns a set of repositories blacklisted """
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


def filter_by_repositories(to_install):
    """ Filter packages to be installed based on repositories"""
    blacklisted_pkgs = set()
    for pkg, repo in to_install.items():
        if repo in get_repositories_blacklisted():
            blacklisted_pkgs.add(pkg)
            del to_install[pkg]

    if blacklisted_pkgs:
        report_skipped_packages('packages will not be installed due to blacklisted repositories:',
                                blacklisted_pkgs)


def map_repositories(to_install):
    """ Map repositories from PES data to RHSM repository id """
    repo_not_mapped_pkgs = set()
    for pkg, repo in to_install.items():
        if repo not in REPOSITORIES_MAPPING:
            repo_not_mapped_pkgs.add(pkg)
            del to_install[pkg]
            continue

        to_install[pkg] = REPOSITORIES_MAPPING[repo]

    if repo_not_mapped_pkgs:
        report_skipped_packages('packages will not be installed due to not mapped repositories:',
                                repo_not_mapped_pkgs)


def process_events(events):
    """ Process PES Events and generate Leapp messages """
    to_install = {}
    to_remove = {}

    for event in events:
        to_install.update(event.out_pkgs)

        if event.action not in ('Present', 'Deprecated', 'Moved') and event.in_pkgs:
            to_remove.update(event.in_pkgs)

    filter_by_repositories(to_install)
    map_repositories(to_install)

    to_install_pkgs = set(to_install.keys())
    to_remove_pkgs = set(to_remove.keys())

    common = to_install_pkgs.intersection(to_remove_pkgs)
    to_install_pkgs.difference_update(common)
    to_remove_pkgs.difference_update(common)

    if to_install_pkgs or to_remove_pkgs:
        api.produce(RpmTransactionTasks(to_install=list(to_install_pkgs),
                                        to_remove=list(to_remove_pkgs)))

    to_enable_repos = set(to_install.values())

    if to_enable_repos:
        api.produce(RepositoriesSetupTasks(to_enable=list(to_enable_repos)))


def scan_events(path):
    """ Scan JSON file containing PES events """
    try:
        events = parse_file(path)
    except (ValueError, KeyError):
        title = 'Missing/Invalid PES data file ({})'.format(path)
        summary = 'Read documentation at: https://access.redhat.com/articles/3664871 for more information ' \
            'about how to retrieve the files'
        reporting.report_generic(title=title, summary=summary, severity='high', flags=['inhibitor'])
        raise StopActorExecution()

    process_events(filter_events(events))
