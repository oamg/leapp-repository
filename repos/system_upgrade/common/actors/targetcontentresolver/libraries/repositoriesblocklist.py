from leapp import reporting
from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesBlocklisted


def _report_excluded_repos(repos):
    api.current_logger().info(
        'The CRB repository is not enabled. Excluding {} from the upgrade'.format(repos)
    )

    report = [
        reporting.Title('Excluded target system repositories'),
        reporting.Summary(
            'The following repositories are not supported by '
            'Red Hat and are excluded from the list of repositories '
            'used during the upgrade.\n- {}'.format('\n- '.join(repos))
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Remediation(
            hint=(
                'If some of excluded repositories are still required to be used'
                ' during the upgrade, execute leapp with the --enablerepo option'
                ' with the repoid of the repository required to be enabled'
                ' as an argument (the option can be used multiple times).'
            )
        ),
        reporting.Key('1b9132cb2362ae7830e48eee7811be9527747de8')
    ]
    reporting.create_report(report)


def _get_crb_repos(repo_mapping,  flag_source_os):
    """
    Return set of relevant CRB repoids for the source or target OS.

    :param repo_mapping: Operator to work with the repositories mapping data
    :type repo_mapping: repomap_calc.RepoMapDataHandler
    :param flag_source_os: Set True for the source OS, False for the target OS.
    :type flag_source_os: bool
    :returns: A set of repoids with the specified pesid and major version.
    :rtype: Set[str]
    """
    curr_arch = api.current_actor().configuration.architecture
    if flag_source_os:
        pesid = 'rhel{}-CRB'.format(get_source_major_version())
        crb_repos = repo_mapping.get_source_pesid_repos(pesid)
    else:
        pesid = 'rhel{}-CRB'.format(get_target_major_version())
        crb_repos = repo_mapping.get_target_pesid_repos(pesid)
    return {repo.repoid for repo in crb_repos if repo.arch == curr_arch}


def _are_crb_repos_disabled(repo_mapping, enabled_repoids):
    """
    Checks whether all CRB repositories are disabled.

    :param repo_mapping: Operator to work with the repositories mapping data
    :type repo_mapping: repomap_calc.RepoMapDataHandler
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: False if any CRB repositories are enabled on the source system, True otherwise.
    :rtype: bool
    """
    return enabled_repoids.isdisjoint(_get_crb_repos(repo_mapping, True))


def _calc_internal_blocklist(repo_mapping, external_tasks, enabled_repoids):
    """
    Calculate the internal blocklist of target CRB repositories.

    Conditions to exclude:
    - no CRB repositories are enabled on the source system
    - repository is not explicitly configured by user to be used during the upgrade
      (e.g. via the --enablerepo option or via the /etc/leapp/files/leapp_upgrade_repositories.repo file)

    Also report explicitly enabled and blocklisted CRB repositories, unless
    CRB is already already enabled on the source system.

    :param repo_mapping: Operator to work with the repositories mapping data
    :type repo_mapping: repomap_calc.RepoMapDataHandler
    :param external_tasks: External repositories tasks represented by object with following fields:

        * ``to_enable`` - repositories that should be enabled
        * ``to_block`` - repositories that should be blocklisted
        * ``custom`` - repositories explicitly requested by user to be used during the upgrade

    :type external_tasks: targetcontentresolver.ExternalRepoSetupTasks
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: Set of CRB repoids to blocklist on the target system.
    :rtype: Set[str]
    """
    if not _are_crb_repos_disabled(repo_mapping, enabled_repoids):
        # nothing to do - a CRB repo is enabled
        return set()

    repos_to_exclude = _get_crb_repos(repo_mapping, False)

    # Do not exclude repositories explicitly required by user for the upgrade
    manually_enabled_repos = external_tasks.custom & repos_to_exclude

    if manually_enabled_repos:
        # NOTE(pstodulk): Same like in case that a CRB repo is enabled on src OS
        return set()

    if get_target_distro_id() == 'rhel':
        # TODO(pstodulk): unify reports about blocklisted repos and effect on
        # rpms tasks in pes_events_scanner
        _report_excluded_repos(repos_to_exclude)

    return repos_to_exclude


def compute_blocklist(repo_mapping, external_tasks, enabled_repoids):
    """
    Create the blocklist of repositories that should be blocked during the upgrade.

    Additional effects:
      * Once the list is calculated the RepositoriesBlocklisted message is produced.
      * Generate reports related CRB repositories

    The content in the CRB repository is considered as unsupported. Hence
    we do not want to enable such a repository by default on the target system
    unless
      * it is explicitly requested, or
      * it is already enabled on the source system
    This is important as some functionality originally supported on the source
    source system can be moved to the CRB repository on the target system.
    In such a case, we do not want to install automatically such a content
    that lost a support.

    For this reason, compute the list of repositories that should be blocklisted
    and take into account also external requests.
    In case that multiple requests are raised for a specific repository, the
    priority order is following:
        internal block rq > external enable rq > external block rq > external custom rq

    The external custom request has the highest priority as this comes from
    the system configuration or from the `--enablerepo` option used when executing
    leapp - so it's understood as decision made by user explicitly for
    the in-place upgrade purpose. Currently there is no explicit custom
    configuration to disable a repo.

    :param repo_mapping: Operator to work with the repositories mapping data
    :type repo_mapping: repomap_calc.RepoMapDataHandler
    :param external_tasks: External repositories tasks represented by object with following fields:

        * ``to_enable`` - repositories that should be enabled
        * ``to_block`` - repositories that should be blocklisted
        * ``custom`` - repositories explicitly requested by user to be used during the upgrade

    :type external_tasks: targetcontentresolver.ExternalRepoSetupTasks
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: List of blocklisted repositories
    :rtype: List[str]
    """
    internal_blocklist = _calc_internal_blocklist(repo_mapping, external_tasks, enabled_repoids)
    full_blocklist = internal_blocklist.union(external_tasks.to_block)
    if full_blocklist:
        api.produce(RepositoriesBlocklisted(repoids=sorted(full_blocklist)))

    return full_blocklist
