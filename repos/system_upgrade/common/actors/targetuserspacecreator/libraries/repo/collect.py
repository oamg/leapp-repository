import os

from leapp.libraries.common import repofileutils, rhsm, rhui
from leapp.libraries.stdlib import api
from leapp.libraries.common.config.version import get_target_major_version
from leapp.exceptions import StopActorExecution
from leapp import reporting
from leapp.models import TargetRepositories


def _inhibit_on_duplicate_repos(repofiles):
    """
    Inhibit the upgrade if any repoid is defined multiple times.

    When that happens, it not only shows misconfigured system, but then
    we can't get details of all the available repos as well.
    """
    # TODO: this is is duplicate of rhsm._inhibit_on_duplicate_repos
    # Issue: #486
    duplicates = repofileutils.get_duplicate_repositories(repofiles).keys()

    if not duplicates:
        return
    list_separator_fmt = '\n    - '
    api.current_logger().warning(
        'The following repoids are defined multiple times:{0}{1}'
        .format(list_separator_fmt, list_separator_fmt.join(duplicates))
    )

    reporting.create_report([
        reporting.Title('A YUM/DNF repository defined multiple times'),
        reporting.Summary(
            'The following repositories are defined multiple times inside the'
            ' "upgrade" container:{0}{1}'
            .format(list_separator_fmt, list_separator_fmt.join(duplicates))
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Tags([reporting.Tags.REPOSITORY]),
        reporting.Flags([reporting.Flags.INHIBITOR]),
        reporting.Remediation(hint=(
            'Remove the duplicate repository definitions or change repoids of'
            ' conflicting repositories on the system to prevent the'
            ' conflict.'
            )
        )
    ])


def _get_all_available_repoids(context):
    repofiles = repofileutils.get_parsed_repofiles(context)
    # TODO: this is not good solution, but keep it as it is now
    # Issue: #486
    if rhsm.skip_rhsm():
        # only if rhsm is skipped, the duplicate repos are not detected
        # automatically and we need to do it extra
        _inhibit_on_duplicate_repos(repofiles)
    repoids = []
    for rfile in repofiles:
        if rfile.data:
            repoids += [repo.repoid for repo in rfile.data]
    return set(repoids)


def _get_rhsm_available_repoids(context):
    target_major_version = get_target_major_version()
    # FIXME: check that required repo IDs (baseos, appstream)
    # + or check that all required RHEL repo IDs are available.
    if rhsm.skip_rhsm():
        return set()
    # Get the RHSM repos available in the target RHEL container
    # TODO: very similar thing should happens for all other repofiles in container
    #
    repoids = rhsm.get_available_repo_ids(context)
    if not repoids or len(repoids) < 2:
        reporting.create_report([
            reporting.Title('Cannot find required basic RHEL target repositories.'),
            reporting.Summary(
                'This can happen when a repository ID was entered incorrectly either while using the --enablerepo'
                ' option of leapp or in a third party actor that produces a CustomTargetRepositoryMessage.'
            ),
            reporting.Tags([reporting.Tags.REPOSITORY]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.Remediation(hint=(
                'It is required to have RHEL repositories on the system'
                ' provided by the subscription-manager unless the --no-rhsm'
                ' option is specified. You might be missing a valid SKU for'
                ' the target system or have a failed network connection.'
                ' Check whether your system is attached to a valid SKU that is'
                ' providing RHEL {} repositories.'
                ' If you are using Red Hat Satellite, read the upgrade documentation'
                ' to set up Satellite and the system properly.'

            ).format(target_major_version)),
            reporting.ExternalLink(
                # TODO: How to handle different documentation links for each version?
                url='https://red.ht/preparing-for-upgrade-to-rhel8',
                title='Preparing for the upgrade')
            ])
        raise StopActorExecution()
    return set(repoids)


def _get_rhui_available_repoids(context, cloud_repo):
    repofiles = repofileutils.get_parsed_repofiles(context)

    # TODO: same refactoring as Issue #486?
    _inhibit_on_duplicate_repos(repofiles)
    repoids = []
    for rfile in repofiles:
        if rfile.file == cloud_repo and rfile.data:
            repoids = [repo.repoid for repo in rfile.data]
            repoids.sort()
            break
    return set(repoids)


def _get_rh_available_repoids(context, indata):
    """
    RH repositories are provided either by RHSM or are stored in the expected repo file provided by
    RHUI special packages (every cloud provider has itw own rpm).
    """

    upg_path = rhui.get_upg_path()

    rh_repoids = _get_rhsm_available_repoids(context)

    if indata and indata.rhui_info:
        cloud_repo = os.path.join(
            '/etc/yum.repos.d/', rhui.RHUI_CLOUD_MAP[upg_path][indata.rhui_info.provider]['leapp_pkg_repo']
        )
        rhui_repoids = _get_rhui_available_repoids(context, cloud_repo)
        rh_repoids.update(rhui_repoids)

    return rh_repoids


def gather_target_repositories(context, indata):
    """
    Get available required target repositories and inhibit or raise error if basic checks do not pass.

    In case of repositories provided by Red Hat, it's checked whether the basic
    required repositories are available (or at least defined) in the given
    context. If not, raise StopActorExecutionError.

    For the custom target repositories we expect all of them have to be defined.
    If any custom target repository is missing, raise StopActorExecutionError.

    If any repository is defined multiple times, produce the inhibitor Report
    msg.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: List of target system repoids
    :rtype: List(string)
    """
    rh_available_repoids = _get_rh_available_repoids(context, indata)
    all_available_repoids = _get_all_available_repoids(context)

    target_repoids = []
    missing_custom_repoids = []
    for target_repo in api.consume(TargetRepositories):
        for rhel_repo in target_repo.rhel_repos:
            if rhel_repo.repoid in rh_available_repoids:
                target_repoids.append(rhel_repo.repoid)
            else:
                # TODO: We shall report that the RHEL repos that we deem necessary for
                # the upgrade are not available; but currently it would just print bunch of
                # data everytime as we maps EUS and other repositories as well. But these
                # do not have to be necessary available on the target system in the time
                # of the upgrade. Let's skip it for now until it's clear how we will deal
                # with it.
                pass
        for custom_repo in target_repo.custom_repos:
            if custom_repo.repoid in all_available_repoids:
                target_repoids.append(custom_repo.repoid)
            else:
                missing_custom_repoids.append(custom_repo.repoid)
    api.current_logger().debug("Gathered target repositories: {}".format(', '.join(target_repoids)))
    if not target_repoids:
        reporting.create_report([
            reporting.Title('There are no enabled target repositories'),
            reporting.Summary(
                'This can happen when a system is not correctly registered with the subscription manager'
                ' or, when the leapp --no-rhsm option has been used, no custom repositories have been'
                ' passed on the command line.'
            ),
            reporting.Tags([reporting.Tags.REPOSITORY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(hint=(
                'Ensure the system is correctly registered with the subscription manager and that'
                ' the current subscription is entitled to install the requested target version {version}.'
                ' If you used the --no-rhsm option (or the LEAPP_NO_RHSM=1 environment variable is set),'
                ' ensure the custom repository file is provided with'
                ' properly defined repositories and that the --enablerepo option for leapp is set if the'
                ' repositories are defined in any repofiles under the /etc/yum.repos.d/ directory.'
                ' For more information on custom repository files, see the documentation.'
                ' Finally, verify that the "/etc/leapp/files/repomap.json" file is up-to-date.'
            ).format(version=api.current_actor().configuration.version.target)),
            reporting.ExternalLink(
                # TODO: How to handle different documentation links for each version?
                url='https://red.ht/preparing-for-upgrade-to-rhel8',
                title='Preparing for the upgrade'),
            reporting.RelatedResource("file", "/etc/leapp/files/repomap.json"),
            reporting.RelatedResource("file", "/etc/yum.repos.d/")
        ])
        raise StopActorExecution()
    if missing_custom_repoids:
        reporting.create_report([
            reporting.Title('Some required custom target repositories have not been found'),
            reporting.Summary(
                'This can happen when a repository ID was entered incorrectly either'
                ' while using the --enablerepo option of leapp, or in a third party actor that produces a'
                ' CustomTargetRepositoryMessage.\n'
                'The following repositories IDs could not be found in the target configuration:\n'
                '- {}\n'.format('\n- '.join(missing_custom_repoids))
            ),
            reporting.Tags([reporting.Tags.REPOSITORY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.ExternalLink(
                # TODO: How to handle different documentation links for each version?
                url='https://access.redhat.com/articles/4977891',
                title='Customizing your Red Hat Enterprise Linux in-place upgrade'),
            reporting.Remediation(hint=(
                'Consider using the custom repository file, which is documented in the official'
                ' upgrade documentation. Check whether a repository ID has been'
                ' entered incorrectly with the --enablerepo option of leapp.'
                ' Check the leapp logs to see the list of all available repositories.'
            ))
        ])
        raise StopActorExecution()
    return set(target_repoids)


def _gather_target_repositories(context, indata, prod_cert_path):
    """
    This is wrapper function to gather the target repoids.

    Probably the function could be partially merged into gather_target_repositories
    and this could be really just wrapper with the switch of certificates.
    I am keeping that for now as it is as interim step.

    :param context: the container where the repofiles should be copied
    :type context: mounting.IsolatedActions class
    :param indata: majority of input data for the actor
    :type indata: class _InputData
    :param prod_cert_path: path where the target product cert is stored
    :type prod_cert_path: string
    """
    rhsm.set_container_mode(context)
    rhsm.switch_certificate(context, indata.rhsm_info, prod_cert_path)
    if indata.rhui_info:
        rhui.copy_rhui_data(context, indata.rhui_info.provider)
    _install_custom_repofiles(context, indata.custom_repofiles)
    return gather_target_repositories(context, indata)
