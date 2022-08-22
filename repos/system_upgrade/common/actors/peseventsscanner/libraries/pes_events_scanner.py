from collections import namedtuple
from functools import partial

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import peseventsscanner_repomap
from leapp.libraries.actor.pes_event_parsing import Action, get_pes_events, Package
from leapp.libraries.common.config import version
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

SKIPPED_PKGS_MSG = (
    'packages will be skipped because they are available only in '
    'target system repositories that are intentionally excluded from the '
    'list of repositories used during the upgrade. '
    'See the report message titled "Excluded target system repositories" '
    'for details.\nThe list of these packages:'
)


TransactionConfiguration = namedtuple('TransactionConfiguration', ('to_install', 'to_remove', 'to_keep'))


def get_cloud_provider_name(cloud_provider_variant):
    for cloud_provider_prefix in ('aws', 'azure', 'google'):
        if cloud_provider_variant.startswith(cloud_provider_prefix):
            return cloud_provider_prefix
    return cloud_provider_variant


def get_best_pesid_candidate(candidate_a, candidate_b, cloud_provider):
    cdn_candidate = None
    for candidate in (candidate_a, candidate_b):
        if candidate.rhui == cloud_provider:
            return candidate
        if not candidate.rhui:
            cdn_candidate = candidate

    # None of the candidate matches cloud provider and none of them is from CDN -
    # do not return anything as we don't want to get content from different cloud providers
    return cdn_candidate


def get_installed_pkgs():
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
        installed_pkgs.add(Package(name=pkg.name, repository=pkg.repository, modulestream=modulestream))

    return installed_pkgs


def get_transaction_configuration():
    """
    Get pkgs to install, keep and remove from the user configuration files in /etc/leapp/transaction/.

    These configuration files have higher priority than PES data.
    :return: RpmTransactionTasks model instance
    """
    transaction_configuration = TransactionConfiguration(to_install=[], to_remove=[], to_keep=[])

    _Pkg = partial(Package, repository=None, modulestream=None)

    for tasks in api.consume(RpmTransactionTasks):
        transaction_configuration.to_install.extend(_Pkg(name=pkg_name) for pkg_name in tasks.to_install)
        transaction_configuration.to_remove.extend(_Pkg(name=pkg_name) for pkg_name in tasks.to_remove)
        transaction_configuration.to_keep.extend(_Pkg(name=pkg_name) for pkg_name in tasks.to_keep)
    return transaction_configuration


def get_relevant_releases(events):
    """
    Get releases present in the PES Events that are relevant for this IPU.

    Relevant release happened between the source OS version and the target OS version.
    """
    # Collect releases that happened between source OS version and target OS version
    relevant_releases_match_list = [
        '> {0}'.format(api.current_actor().configuration.version.source),
        '<= {0}'.format(api.current_actor().configuration.version.target)
    ]
    releases = {event.to_release for event in events}
    releases = [r for r in releases if version.matches_version(relevant_releases_match_list, '{}.{}'.format(*r))]
    return sorted(releases)


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


def compute_pkg_changes_between_consequent_releases(source_installed_pkgs,
                                                    events,
                                                    release,
                                                    seen_pkgs,
                                                    pkgs_to_demodularize):
    # Start with the installed packages and modify the set according to release events
    target_pkgs = set(source_installed_pkgs)

    release_events = [e for e in events if e.to_release == release]

    for event in release_events:
        # PRESENCE events have a different semantics than the other events - they add a package to a target state
        # only if it had been seen (installed) during the course of the overall target packages
        if event.action == Action.PRESENT:
            for pkg in event.in_pkgs:
                if pkg in seen_pkgs:
                    if pkg in target_pkgs:
                        # Remove the package with the old repository, add the one with the new one
                        target_pkgs.remove(pkg)
                    target_pkgs.add(pkg)
        elif event.action == Action.DEPRECATED:
            if event.in_pkgs.intersection(source_installed_pkgs):
                # Remove packages with old repositories add packages with the new one
                target_pkgs = target_pkgs.difference(event.in_pkgs)
                target_pkgs = target_pkgs.union(event.in_pkgs)
        else:
            # All other packages have the same semantics - they remove their in_pkgs from the system with given
            # from_release and add out_pkgs to the system matching to_release
            are_all_in_pkgs_present = all(in_pkg in source_installed_pkgs for in_pkg in event.in_pkgs)
            is_any_in_pkg_present = any(in_pkg in source_installed_pkgs for in_pkg in event.in_pkgs)

            # For MERGE to be relevant it is sufficient for only one of its in_pkgs to be installed
            if are_all_in_pkgs_present or (event.action == Action.MERGED and is_any_in_pkg_present):
                # In pkgs are present, event can be applied
                target_pkgs = target_pkgs.difference(event.in_pkgs)
                target_pkgs = target_pkgs.union(event.out_pkgs)

        pkgs_to_demodularize = pkgs_to_demodularize.difference(event.in_pkgs)

    return (target_pkgs, pkgs_to_demodularize)


def compute_packages_on_target_system(source_pkgs, events, releases):

    seen_pkgs = set(source_pkgs)  # Used to track whether PRESENCE events can be applied
    target_pkgs = set(source_pkgs)

    source_major_version = int(version.get_source_major_version())
    did_processing_cross_major_version = False
    pkgs_to_demodularize = set()  # Modified by compute_pkg_changes

    for release in releases:
        if not did_processing_cross_major_version and release[0] > source_major_version:
            did_processing_cross_major_version = True
            pkgs_to_demodularize = {pkg for pkg in target_pkgs if pkg.modulestream}

        target_pkgs, pkgs_to_demodularize = compute_pkg_changes_between_consequent_releases(target_pkgs, events,
                                                                                            release, seen_pkgs,
                                                                                            pkgs_to_demodularize)
        seen_pkgs = seen_pkgs.union(target_pkgs)

    demodularized_pkgs = {Package(pkg.name, pkg.repository, None) for pkg in pkgs_to_demodularize}
    demodularized_target_pkgs = target_pkgs.difference(pkgs_to_demodularize).union(demodularized_pkgs)

    return (demodularized_target_pkgs, pkgs_to_demodularize)


def compute_rpm_tasks_from_pkg_set_diff(source_pkgs, target_pkgs, pkgs_to_demodularize):
    source_state_pkg_names = {pkg.name for pkg in source_pkgs}
    target_state_pkg_names = {pkg.name for pkg in target_pkgs}

    pkgs_to_install = sorted(target_state_pkg_names.difference(source_state_pkg_names))
    pkgs_to_remove = sorted(source_state_pkg_names.difference(target_state_pkg_names))

    if pkgs_to_install or pkgs_to_remove:
        # NOTE(mhecko): Here we do not want to consider any package that does not have a reference in PES data. There
        # might be missing modularity information, and although the algorithm is correct, trying to enable
        # a non-existent modulestream due to missing modulestream information results in a crash.
        target_pkgs_without_demodularized_pkgs = target_pkgs.difference(pkgs_to_demodularize)

        # Collect the enabled modules as tuples in a set, so we produce every module to reset exactly once
        enabled_modules = {(module.name, module.stream) for module in _get_enabled_modules()}
        modules_to_reset = [Module(name=ms[0], stream=ms[1]) for ms in enabled_modules]

        target_modulestreams = {pkg.modulestream for pkg in target_pkgs_without_demodularized_pkgs if pkg.modulestream}
        modules_to_enable = [Module(name=ms[0], stream=ms[1]) for ms in target_modulestreams]

        return PESRpmTransactionTasks(to_install=pkgs_to_install,
                                      to_remove=pkgs_to_remove,
                                      modules_to_enable=modules_to_enable,
                                      modules_to_reset=modules_to_reset)
    return None


def report_skipped_packages(title, message, skipped_pkgs, remediation=None):
    skipped_pkgs = sorted(skipped_pkgs)

    def make_summary_entry_for_skipped_pkg(pkg):
        entry_template = '- {name}{modulestream} (repoid: {repository})'
        modulestream_str = '' if not pkg.modulestream else '[{}:{}]'.format(*pkg.modulestream)
        return entry_template.format(name=pkg.name, modulestream=modulestream_str, repository=pkg.repository)

    summary = '{} {}\n{}'.format(len(skipped_pkgs),
                                 message,
                                 '\n'.join(make_summary_entry_for_skipped_pkg(pkg) for pkg in skipped_pkgs))
    report_content = [
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.REPOSITORY]),
    ]
    if remediation:
        report_content += [reporting.Remediation(hint=remediation)]
    report_content += [reporting.RelatedResource('package', p[0]) for p in skipped_pkgs]
    reporting.create_report(report_content)
    if is_verbose():
        api.current_logger().info(summary)


def remove_new_packages_from_blacklisted_repos(source_pkgs, target_pkgs):
    """
    Remove newly installed packages from blacklisted repositories that were computed to be on the target system.
    """
    blacklisted_repoids = get_blacklisted_repoids()
    new_pkgs = target_pkgs.difference(source_pkgs)
    pkgs_from_blacklisted_repos = set(pkg for pkg in new_pkgs if pkg.repository in blacklisted_repoids)

    if pkgs_from_blacklisted_repos:
        report_skipped_packages(
            title='Packages available in excluded repositories will not be installed',
            message=SKIPPED_PKGS_MSG,
            skipped_pkgs=pkgs_from_blacklisted_repos,
        )
    return blacklisted_repoids, target_pkgs.difference(pkgs_from_blacklisted_repos)


def get_blacklisted_repoids():
    repos_blacklisted = set()
    for blacklist in api.consume(RepositoriesBlacklisted):
        repos_blacklisted.update(blacklist.repoids)
    return repos_blacklisted


def get_enabled_repoids():
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


def get_pesid_to_repoid_map(target_pesids):
    """
    Get a dictionary mapping all PESID repositories to their corresponding repoid.

    :param target_pesids: The set of target PES IDs needed to be mapped
    :return: Dictionary mapping the target_pesids to their corresponding repoid
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

    # NOTE: We have to calculate expected target repositories like in the setuptargetrepos actor.
    # It's planned to handle this in different a way in future...

    enabled_repoids = get_enabled_repoids()
    default_channels = peseventsscanner_repomap.get_default_repository_channels(repomap, enabled_repoids)
    repomap.set_default_channels(default_channels)

    exp_pesid_repos = repomap.get_expected_target_pesid_repos(enabled_repoids)
    # FIXME: this is hack now. In case some packages will need a repository
    # with pesid that is not mapped by default regarding the enabled repos,
    # let's use this one representative repository (baseos/appstream) to get
    # data for a guess of the best repository from the requires target pesid..
    # FIXME: this could now fail in case all repos are disabled...
    representative_repo = exp_pesid_repos.get(
        peseventsscanner_repomap.DEFAULT_PESID[version.get_target_major_version()], None
    )
    if not representative_repo:
        api.current_logger().warning('Cannot determine the representative target base repository.')
        api.current_logger().info(
            'Fallback: Create an artificial representative PESIDRepositoryEntry for the repository mapping'
        )
        representative_repo = PESIDRepositoryEntry(
            pesid=peseventsscanner_repomap.DEFAULT_PESID[version.get_target_major_version()],
            arch=api.current_actor().configuration.architecture,
            major_version=version.get_target_major_version(),
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
            api.current_logger().warning('Cannot find suitable repository for PES ID: {}'.format(pesid))
            continue
        pesid_repo = repomap._find_repository_target_equivalent(representative_repo, pesid)

        if not pesid_repo:
            api.current_logger().warning('Cannot find suitable repository for PES ID: {}'.format(pesid))
            continue
        exp_pesid_repos[pesid] = pesid_repo

    # Map just pesids to their corresponding repoids ({to_pesid: repoid})
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


def replace_pesids_with_repoids_in_packages(packages, source_pkgs_repoids):
    """Replace packages with PESID in their .repository field with ones that have repoid providing the package."""
    # We want to map only PESIDs - if some package had no events, it will its repository set to source system repoid
    packages_with_pesid = {pkg for pkg in packages if pkg.repository not in source_pkgs_repoids}
    packages_without_pesid = packages.difference(packages_with_pesid)

    required_target_pesids = {pkg.repository for pkg in packages_with_pesid}

    pesid_to_repoid_map = get_pesid_to_repoid_map(required_target_pesids)

    packages_without_known_repoid = {pkg for pkg in packages_with_pesid if pkg.repository not in pesid_to_repoid_map}

    if packages_without_known_repoid:
        report_skipped_packages(
            title='Packages from unknown repositories may not be installed',
            message='packages may not be installed or upgraded due to repositories unknown to leapp:',
            skipped_pkgs=packages_without_known_repoid,
            remediation=(
                'Please file a bug in http://bugzilla.redhat.com/ for leapp-repository component of '
                'the Red Hat Enterprise Linux product.'
            ),
        )

    packages_with_known_repoid = packages_with_pesid.difference(packages_without_known_repoid)
    packages_with_repoid = {
        Package(p.name, pesid_to_repoid_map[p.repository], p.modulestream) for p in packages_with_known_repoid
    }
    # Packages without pesid are those for which we do not have an event, keep them in target packages
    return packages_with_repoid.union(packages_without_pesid)


def apply_transaction_configuration(source_pkgs):
    source_pkgs_with_conf_applied = set(source_pkgs)
    transaction_configuration = get_transaction_configuration()

    source_pkgs_with_conf_applied = source_pkgs.union(transaction_configuration.to_install)

    # Transaction configuration contains only names of packages to install/remove/keep - there is no modularity
    # information - modify target_pkgs in a way ignoring modulestream information
    pkg_name_to_pkg_info_map = {pkg.name: pkg for pkg in source_pkgs}

    for pkg in transaction_configuration.to_remove:
        if pkg.name in pkg_name_to_pkg_info_map:
            source_pkgs_with_conf_applied.remove(pkg_name_to_pkg_info_map[pkg.name])

    for pkg in transaction_configuration.to_keep:
        if pkg.name in pkg_name_to_pkg_info_map:
            source_pkgs_with_conf_applied.add(pkg_name_to_pkg_info_map[pkg.name])

    return source_pkgs_with_conf_applied


def process():
    # Retrieve data - installed_pkgs, transaction configuration, pes events
    events = get_pes_events('/etc/leapp/files', 'pes-events.json')
    releases = get_relevant_releases(events)
    source_pkgs = get_installed_pkgs()
    source_pkgs = apply_transaction_configuration(source_pkgs)

    # Keep track of what repoids have the source packages to be able to determine what are the PESIDs of the computed
    # packages of the target system, so we can distinguish what needs to be repomapped
    repoids_of_source_pkgs = {pkg.repository for pkg in source_pkgs}

    # Apply events - compute what packages should the target system have
    target_pkgs, pkgs_to_demodularize = compute_packages_on_target_system(source_pkgs, events, releases)

    # Packages coming out of the events have PESID as their repository, however, we need real repoid
    target_pkgs = replace_pesids_with_repoids_in_packages(target_pkgs, repoids_of_source_pkgs)

    # Apply the desired repository blacklisting
    blacklisted_repoids, target_pkgs = remove_new_packages_from_blacklisted_repos(source_pkgs, target_pkgs)

    # Look at the target packages and determine what repositories to enable
    target_repoids = sorted(set(p.repository for p in target_pkgs) - blacklisted_repoids - repoids_of_source_pkgs)
    repos_to_enable = RepositoriesSetupTasks(to_enable=target_repoids)
    api.produce(repos_to_enable)

    # Compare the packages on source system and the computed packages on target system and determine what to install
    rpm_tasks = compute_rpm_tasks_from_pkg_set_diff(source_pkgs, target_pkgs, pkgs_to_demodularize)
    if rpm_tasks:
        api.produce(rpm_tasks)
