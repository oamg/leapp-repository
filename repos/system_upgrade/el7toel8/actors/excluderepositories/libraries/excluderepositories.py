from leapp import reporting
from leapp.libraries.common.config import get_product_type
from leapp.libraries.stdlib import api
from leapp.models import (
    CustomTargetRepository,
    RepositoriesBlacklisted,
    RepositoriesExcluded,
    RepositoriesFacts,
    RepositoriesMap,
)

manually_enabled_repos_in_use = []


def _report_using_unsupported_repos():
    if manually_enabled_repos_in_use:
        report = [
            reporting.Title("Using repository not supported by Red Hat"),
            reporting.Summary(
                "The following repository has been used for the "
                "upgrade, but it is not supported by the Red Hat.:\n"
                "- {}".format("\n - ".join(manually_enabled_repos_in_use))
            ),
            reporting.ExternalLink(
                url=(
                    "https://access.redhat.com/documentation/en-us/"
                    "red_hat_enterprise_linux/8/html/package_manifest/"
                    "codereadylinuxbuilder-repository."
                ),
                title="CodeReady Linux Builder repository",
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Tags([reporting.Tags.REPOSITORY]),
        ]
        reporting.create_report(report)


def _is_optional_repo(repo):
    sys_type = get_product_type('source')
    suffix = 'optional-rpms'
    if sys_type != 'ga':
        suffix = 'optional-{}-rpms'.format(sys_type)
    return repo.from_repoid.endswith(suffix)


def _manually_enabled_repo(repo, custom_target_repos):
    """Check if the repo is manually enabled (by --enablerepo option).

    In case the repo was manually enabled, also update the
    manually_enabled_repos_in_use variable
    """
    global manually_enabled_repos_in_use  # pylint: disable-msg=global-statement
    for enabled_repo in custom_target_repos:
        if enabled_repo.repoid == repo.to_repoid:
            if repo.to_repoid not in manually_enabled_repos_in_use:
                manually_enabled_repos_in_use.append(repo.to_repoid)
                api.current_logger().info(
                    "Manually enabled repository %s found. ", repo.to_repoid
                )
            return True
    return False


def _get_optional_repo_mapping():
    """Get a dict of optional repositories based on RepositoriesMap: { 'from_repoid' : 'to_repoid'}.

    It consumes RepositoriesMap messages and create map (dict) of optional repositories
    on RHEL 7 system to CRB repositories on RHEL 8. See the RepositoriesMap model..

    If the repository was manually enabled (specified in --enablerepo option),
    then it will be skipped from adding to the optional repo mapping.
    """
    opt_repo_mapping = {}
    repo_map = next(api.consume(RepositoriesMap), None)
    custom_target_repos = tuple(api.consume(CustomTargetRepository))
    if repo_map:
        for repo in repo_map.repositories:
            if _is_optional_repo(repo) and not _manually_enabled_repo(
                repo, custom_target_repos
            ):
                opt_repo_mapping[repo.from_repoid] = repo.to_repoid
    return opt_repo_mapping


def _get_repos_to_exclude():
    """Get a list of repoids to not use during the upgrade.

    These are such RHEL 8 repositories that mapped to disabled RHEL7 Optional
    repositories.
    """
    opt_repo_mapping = _get_optional_repo_mapping()
    repos_to_exclude = []
    repos_on_system = next(api.consume(RepositoriesFacts), None)
    for repo_file in repos_on_system.repositories:
        for repo in repo_file.data:
            if repo.repoid in opt_repo_mapping and not repo.enabled:
                repos_to_exclude.append(opt_repo_mapping[repo.repoid])
    return repos_to_exclude


def process():
    """Exclude the RHEL8 CRB repo if the RHEL7 optional repo is not enabled.

    If the RHEL8 repo was manually enabled (
        specified by --enablerepo option of the leapp command or
        inside the /etc/leapp/files/leapp_upgrade_repositories.repo),
    )
    then it won't be excluded in case of having matching RHEL7
    repo which is optional.
    """
    repos_to_exclude = _get_repos_to_exclude()
    if manually_enabled_repos_in_use:
        _report_using_unsupported_repos()
    if repos_to_exclude:
        api.current_logger().info(
            "The optional repository is not enabled. Excluding %r "
            "from the upgrade",
            repos_to_exclude,
        )
        api.produce(RepositoriesExcluded(repoids=repos_to_exclude))
        api.produce(RepositoriesBlacklisted(repoids=repos_to_exclude))

        report = [
            reporting.Title("Excluded RHEL 8 repositories"),
            reporting.Summary(
                "The following repositories are not supported by "
                "Red Hat and are excluded from the list of repositories "
                "used during the upgrade.\n- {}".format(
                    "\n- ".join(repos_to_exclude)
                )
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Tags([reporting.Tags.REPOSITORY]),
            reporting.Flags([reporting.Flags.FAILURE]),
            reporting.ExternalLink(
                url=(
                    "https://access.redhat.com/documentation/en-us/"
                    "red_hat_enterprise_linux/8/html/package_manifest/"
                    "codereadylinuxbuilder-repository."
                ),
                title="CodeReady Linux Builder repository",
            ),
            reporting.Remediation(
                hint="At your own risk! Use leapp upgrade {}".format(
                    " ".join(
                        ["--enablerepo " + repo for repo in repos_to_exclude]
                    )
                )
            ),
        ]
        reporting.create_report(report)
