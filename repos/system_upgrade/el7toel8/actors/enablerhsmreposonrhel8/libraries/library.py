from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import CalledProcessError, api, run
from leapp.models import TargetRHSMInfo, UsedTargetRepositories


def set_rhsm_release():
    """Set the RHSM release to the target RHEL 8 minor version."""
    info = next(api.consume(TargetRHSMInfo), None)
    if info and info.release:
        try:
            rhsm.set_release(mounting.NotIsolatedActions(base_dir='/'), info.release)
        except CalledProcessError as err:
            api.current_logger().warning('Unable to set the {0} release through subscription-manager. When using dnf,'
                                         ' content of the latest RHEL 8 minor version will be downloaded.\n{1}'
                                         .format(info.release, str(err)))
    else:
        api.current_logger().debug('Skipping setting the RHSM release due to the use of LEAPP_DEVEL_SKIP_RHSM.')


def enable_rhsm_repos():
    """
    Try enabling all the RHEL 8 repositories that have been used for the upgrade transaction.

    In case of custom repositories, the subscription-manager reports an error that it doesn't know them, but it enables
    the known repositories.
    """
    if rhsm.skip_rhsm():
        api.current_logger().debug('Skipping enabling repositories through subscription-manager due to the use of'
                                   ' LEAPP_DEVEL_SKIP_RHSM.')
        return
    try:
        run(get_submgr_cmd(get_repos_to_enable()))
    except CalledProcessError as err:
        api.current_logger().warning('The subscription-manager could not enable some repositories.\n'
                                     'It is expected behavior in case of custom repositories unknown to'
                                     ' the subscription-manager - these need to be enabled manually.\n{0}'
                                     .format(str(err)))


def get_submgr_cmd(repos_to_enable):
    submgr_cmd = ['subscription-manager', 'repos']
    for repoid in repos_to_enable:
        submgr_cmd += ['--enable', repoid]
    return submgr_cmd


def get_repos_to_enable():
    """
    Return set of repositories used during the upgrade transaction.

    This set may include repos unknown to subscription-manager - notable those added as custom using
    CustomTargetRepository model.
    """
    used_repos_msg = next(api.consume(UsedTargetRepositories), None)
    return {repo.repoid for repo in used_repos_msg.repos}
