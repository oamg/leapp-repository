from leapp import reporting
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import RepositoriesBlocklisted


def _report_using_unsupported_repos(repos):
    report = [
        reporting.Title('Using repository not supported by Red Hat'),
        reporting.Summary(
            'The following repositories have been used for the '
            'upgrade, but they are not supported by the Red Hat.:\n'
            '- {}'.format('\n - '.join(repos))
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Key('e931e4c299de7d276238e5d0b363c010e8587977')
    ]
    reporting.create_report(report)


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


def _get_crb_repos(repo_mapping, major_version):
    """
    Return set of relevant CRB repoids for the specified major version

    Only CRB repositories for the current architecture and distribution are
    relevant.

    :param repo_mapping: RepositoriesMapping message.
    :type repo_mapping: RepositoriesMapping
    :param major_version: The OS major version.
    :type major_version: str
    :returns: A set of repoids with the specified pesid and major version.
    :rtype: Set[str]
    """
    pesid = f'rhel{major_version}-CRB'
    curr_arch = api.current_actor().configuration.architecture
    crb_repoids = set()
    for pesid_repo in repo_mapping.repositories:
        if pesid_repo.major_version != major_version or pesid_repo.arch != curr_arch:
            # irrelevant repository
            continue
        if pesid_repo.pesid == pesid and pesid_repo.major_version == major_version:
            crb_repoids.add(pesid_repo.repoid)
    return crb_repoids


def _are_crb_repos_disabled(repo_mapping, enabled_repoids):
    """
    Checks whether all CRB repositories are disabled.

    :param repo_mapping: RepositoriesMapping message.
    :type repo_mapping: RepositoriesMapping
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: False if any CRB repositories are enabled on the source system, True otherwise.
    :rtype: bool
    """
    return enabled_repoids.isdisjoint(_get_crb_repos(repo_mapping, get_source_major_version()))


def _calc_internal_blocklist(repo_mapping, external_tasks, enabled_repoids):
    """
    Calculate the internal blocklist of target CRB repositories.

    Conditions to exclude:
    - no CRB repositories are enabled on the source system
    - repository is not explicitly configured by user to be used during the upgrade
      (e.g. via the --enablerepo option or via the /etc/leapp/files/leapp_upgrade_repositories.repo file)

    Also report explicitly enabled and blocklisted CRB repositories, unless
    CRB is already already enabled on the source system.

    :param repo_mapping: RepositoriesMapping message.
    :type repo_mapping: RepositoriesMapping
    :param external_tasks: External repositories tasks represented by object with following fields:

        * ``to_enable`` - repositories that should be enabled
        * ``blocklist`` - repositories that should be blocklisted
        * ``custom`` - repositories explicitly requested by user to be used during the upgrade

    :type external_tasks: targetcontentresolver.ExternalRepoSetupTasks
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: Set of CRB repoids to blocklist on the target system.
    :rtype: Set[str]
    """
    if not _are_crb_repos_disabled(repo_mapping, enabled_repoids):
        # nothing to do - no CRB repo is enabled
        return set()

    repos_to_exclude = _get_crb_repos(repo_mapping, get_target_major_version())

    # Do not exclude repositories explicitly required by user for the upgrade
    manually_enabled_repos = external_tasks.custom & repos_to_exclude

    # FIXME(pstodulk): actually, if any target CRB repo is enabled during the
    # upgrade, we should ignore any other as well.
    filtered_repos_to_exclude = repos_to_exclude - manually_enabled_repos

    if manually_enabled_repos:
        # FIXME(pstodulk): This is wrong. This is valid only for RHEL systems
        # and the report itself is confusing - as it is actually only about
        # CRB repositories and not any other.
        _report_using_unsupported_repos(manually_enabled_repos)
    if filtered_repos_to_exclude:
        _report_excluded_repos(filtered_repos_to_exclude)

    return filtered_repos_to_exclude


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

    :param repo_mapping: RepositoriesMapping message.
    :type repo_mapping: RepositoriesMapping
    :param external_tasks: External repositories tasks represented by object with following fields:

        * ``to_enable`` - repositories that should be enabled
        * ``blocklist`` - repositories that should be blocklisted
        * ``custom`` - repositories explicitly requested by user to be used during the upgrade

    :type external_tasks: targetcontentresolver.ExternalRepoSetupTasks
    :param enabled_repoids: Set of repoids enabled on the source system.
    :type enabled_repoids: Set[str]
    :returns: List of blocklisted repositories
    :rtype: List[str]
    """
    internal_blocklist = _calc_internal_blocklist(repo_mapping, external_tasks, enabled_repoids)
    full_blocklist = internal_blocklist.union(external_tasks.blocklist)
    if full_blocklist:
        api.produce(RepositoriesBlocklisted(repoids=sorted(full_blocklist)))

    return full_blocklist
