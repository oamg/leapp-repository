from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, RepositoriesBlacklisted, RepositoriesFacts, RepositoriesMapping

# {OS_MAJOR_VERSION: PESID}
UNSUPPORTED_PESIDS = {
    "7": "rhel7-optional",
    "8": "rhel8-CRB",
    "9": "rhel9-CRB"
}


def _report_using_unsupported_repos(repos):
    report = [
        reporting.Title("Using repository not supported by Red Hat"),
        reporting.Summary(
            "The following repositories have been used for the "
            "upgrade, but they are not supported by the Red Hat.:\n"
            "- {}".format("\n - ".join(repos))
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.REPOSITORY]),
    ]
    reporting.create_report(report)


def _report_excluded_repos(repos):
    optional_repository_name = 'optional' if get_source_major_version() == '7' else 'CRB'
    api.current_logger().info(
        "The {0} repository is not enabled. Excluding {1} from the upgrade".format(optional_repository_name, repos)
    )

    report = [
        reporting.Title("Excluded target system repositories"),
        reporting.Summary(
            "The following repositories are not supported by "
            "Red Hat and are excluded from the list of repositories "
            "used during the upgrade.\n- {}".format("\n- ".join(repos))
        ),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.REPOSITORY]),
        reporting.Groups([reporting.Groups.FAILURE]),
        reporting.Remediation(
            hint=(
                "If some of excluded repositories are still required to be used"
                " during the upgrade, execute leapp with the --enablerepo option"
                " with the repoid of the repository required to be enabled"
                " as an argument (the option can be used multiple times)."
            )
        ),
    ]
    reporting.create_report(report)


def _get_manually_enabled_repos():
    """
    Get a set of repositories (repoids) that are manually enabled.

    manually enabled means (
        specified by --enablerepo option of the leapp command or
        inside the /etc/leapp/files/leapp_upgrade_repositories.repo),
    )
    :rtype: set [repoid]
    """
    try:
        return {repo.repoid for repo in api.consume(CustomTargetRepository)}
    except StopIteration:
        return set()


def _get_pesid_repos(repo_mapping, pesid, major_version):
    """
    Returns a list of pesid repos with the specified pesid and major version.

    :param str pesid: The PES ID representing the family of repositories.
    :param str major_version: The major version of the RHEL OS.
    :returns: A set of repoids with the specified pesid and major version.
    :rtype: List[PESIDRepositoryEntry]
    """
    pesid_repos = []
    for pesid_repo in repo_mapping.repositories:
        if pesid_repo.pesid == pesid and pesid_repo.major_version == major_version:
            pesid_repos.append(pesid_repo)
    return pesid_repos


def _get_repoids_to_exclude(repo_mapping):
    """
    Returns a set of repoids that should be blacklisted on the target system.

    :param RepositoriesMapping repo_mapping: Repository mapping data.
    :returns: A set of repoids to blacklist on the target system.
    :rtype: Set[str]
    """
    pesid_repos_to_exclude = _get_pesid_repos(repo_mapping,
                                              UNSUPPORTED_PESIDS[get_target_major_version()],
                                              get_target_major_version())
    return {pesid_repo.repoid for pesid_repo in pesid_repos_to_exclude}


def _are_optional_repos_disabled(repo_mapping, repos_on_system):
    """
    Checks whether all optional repositories are disabled.

    :param RepositoriesMapping repo_mapping: Repository mapping data.
    :param RepositoriesFacts repos_on_system: Installed repositories on the source system.
    :returns: True if there are any optional repositories enabled on the source system.
    """

    # Get a set of all repo_ids that are optional
    optional_pesid_repos = _get_pesid_repos(repo_mapping,
                                            UNSUPPORTED_PESIDS[get_source_major_version()],
                                            get_source_major_version())

    optional_repoids = [optional_pesid_repo.repoid for optional_pesid_repo in optional_pesid_repos]

    # Gather all optional repositories on the source system that are not enabled
    for repofile in repos_on_system.repositories:
        for repository in repofile.data:
            if repository.repoid in optional_repoids and repository.enabled:
                return False
    return True


def process():
    """
    Exclude target repositories provided by Red Hat without support.

    Conditions to exclude:
    - there are not such repositories already enabled on the source system
      (e.g. "Optional" repositories)
    - such repositories are not required for the upgrade explicitly by the user
      (e.g. via the --enablerepo option or via the /etc/leapp/files/leapp_upgrade_repositories.repo file)

    E.g. CRB repository is provided by Red Hat but it is without the support.
    """

    repo_mapping = next(api.consume(RepositoriesMapping), None)
    repos_facts = next(api.consume(RepositoriesFacts), None)

    # Handle required messages not received
    missing_messages = []
    if not repo_mapping:
        missing_messages.append('RepositoriesMapping')
    if not repos_facts:
        missing_messages.append('RepositoriesFacts')
    if missing_messages:
        raise StopActorExecutionError('Actor didn\'t receive required messages: {0}'.format(
            ', '.join(missing_messages)
        ))

    if not _are_optional_repos_disabled(repo_mapping, repos_facts):
        # nothing to do - an optional repository is enabled
        return

    # Optional repos are either not present or they are present, but disabled -> blacklist them on target system
    repos_to_exclude = _get_repoids_to_exclude(repo_mapping)

    # Do not exclude repos manually enabled from the CLI
    manually_enabled_repos = _get_manually_enabled_repos() & repos_to_exclude
    filtered_repos_to_exclude = repos_to_exclude - manually_enabled_repos

    if manually_enabled_repos:
        _report_using_unsupported_repos(manually_enabled_repos)
    if filtered_repos_to_exclude:
        _report_excluded_repos(filtered_repos_to_exclude)
        api.produce(RepositoriesBlacklisted(repoids=list(filtered_repos_to_exclude)))
