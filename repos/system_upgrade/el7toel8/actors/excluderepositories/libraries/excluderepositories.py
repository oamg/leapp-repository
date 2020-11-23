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


def _report_using_unsupported_repos(repos):
    report = [
        reporting.Title("Using repository not supported by Red Hat"),
        reporting.Summary(
            "The following repository has been used for the "
            "upgrade, but it is not supported by the Red Hat.:\n"
            "- {}".format("\n - ".join(repos))
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


def _report_excluded_repos(repos):
    api.current_logger().info(
        "The optional repository is not enabled. Excluding %r "
        "from the upgrade",
        repos,
    )

    report = [
        reporting.Title("Excluded RHEL 8 repositories"),
        reporting.Summary(
            "The following repositories are not supported by "
            "Red Hat and are excluded from the list of repositories "
            "used during the upgrade.\n- {}".format("\n- ".join(repos))
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
                " ".join(["--enablerepo " + repo for repo in repos])
            )
        ),
    ]
    reporting.create_report(report)


def _is_optional_repo(repo):
    sys_type = get_product_type("source")
    suffix = "optional-rpms"
    if sys_type != "ga":
        suffix = "optional-{}-rpms".format(sys_type)
    return repo.from_repoid.endswith(suffix)


def _get_manually_enabled_repos():
    """Get set of repo that are manually enabled.

    manually enabled means (
        specified by --enablerepo option of the leapp command or
        inside the /etc/leapp/files/leapp_upgrade_repositories.repo),
    )
    :rtype: set [repoid]
    """
    return set(repo.repoid for repo in api.consume(CustomTargetRepository))


def _get_optional_repo_mapping():
    """Get a mapping of RHEL 7 Optional repos to corresponding RHEL 8 repos.

    It consumes RepositoriesMap messages and creates a mapping of 'Optional' repositories
    on RHEL 7 to CRB repositories on RHEL 8.
    It returns the mapping as a dict {'from_repoid' : 'to_repoid'}.
    """
    opt_repo_mapping = {}
    repo_map = next(api.consume(RepositoriesMap), None)
    if repo_map:
        for repo in repo_map.repositories:
            if _is_optional_repo(repo):
                opt_repo_mapping[repo.from_repoid] = repo.to_repoid
    return opt_repo_mapping


def _get_repos_to_exclude():
    """Get a set of repoids to not use during the upgrade.

    These are such RHEL 8 repositories that are mapped to disabled
    RHEL 7 Optional repositories.
    :rtype: set [repoids]
    """
    opt_repo_mapping = _get_optional_repo_mapping()
    repos_to_exclude = []
    repos_on_system = next(api.consume(RepositoriesFacts), None)
    if repos_on_system:
        for repo_file in repos_on_system.repositories:
            for repo in repo_file.data:
                if repo.repoid in opt_repo_mapping and not repo.enabled:
                    repos_to_exclude.append(opt_repo_mapping[repo.repoid])
    return set(repos_to_exclude)


def process():
    """Exclude the RHEL 8 CRB repo if the RHEL 7 optional repo is not enabled.

    If the RHEL8 repo was manually enabled (
        specified by --enablerepo option of the leapp command or
        inside the /etc/leapp/files/leapp_upgrade_repositories.repo),
    )
    then it won't be excluded in case of having matching RHEL 7
    repo which is optional.
    """
    repos_to_exclude = _get_repos_to_exclude()
    manually_enabled_repos = _get_manually_enabled_repos() & repos_to_exclude

    overriden_repos_to_exclude = repos_to_exclude - manually_enabled_repos

    if manually_enabled_repos:
        _report_using_unsupported_repos(manually_enabled_repos)
    if overriden_repos_to_exclude:
        _report_excluded_repos(overriden_repos_to_exclude)
        api.produce(RepositoriesExcluded(repoids=list(repos_to_exclude)))
        api.produce(RepositoriesBlacklisted(repoids=list(repos_to_exclude)))
