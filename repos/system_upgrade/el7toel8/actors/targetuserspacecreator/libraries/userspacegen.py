import itertools
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import constants
from leapp.libraries.common import dnfplugin, mounting, overlaygen, rhsm, utils
from leapp.libraries.stdlib import api, run
from leapp.models import (OSReleaseFacts, RequiredTargetUserspacePackages,
                          SourceRHSMInfo, TargetUserSpaceInfo)


def _logger():
    return api.current_logger()


def prepare_target_userspace(context, userspace_dir, enabled_repos, packages):
    """
    Implements the creation of the target userspace.
    """
    run(['rm', '-rf', userspace_dir])
    _create_target_userspace_directories(userspace_dir)
    with mounting.BindMount(source=userspace_dir, target=os.path.join(context.base_dir, 'el8target')):
        repos_opt = [['--enablerepo', repo] for repo in enabled_repos]
        repos_opt = list(itertools.chain(*repos_opt))
        context.call(
            [
                'dnf',
                'install',
                '-y',
                '--nogpgcheck',
                '--setopt=module_platform_id=platform:el8',
                '--setopt=keepcache=1',
                '--releasever', '8',
                '--installroot', '/el8target',
                '--disablerepo', '*'
            ] + repos_opt + packages,
            callback_raw=utils.logging_handler
        )


def _prep_repository_access(context, target_userspace):
    """
    Prepare repository access by copying all relevant certificates and configuration files to the userspace
    """
    if not rhsm.skip_rhsm():
        run(['rm', '-rf', os.path.join(target_userspace, 'etc', 'pki')])
        run(['rm', '-rf', os.path.join(target_userspace, 'etc', 'rhsm')])
        context.copytree_from('/etc/pki', os.path.join(target_userspace, 'etc', 'pki'))
        context.copytree_from('/etc/rhsm', os.path.join(target_userspace, 'etc', 'rhsm'))
    run(['rm', '-rf', os.path.join(target_userspace, 'etc', 'yum.repos.d')])
    context.copytree_from('/etc/yum.repos.d', os.path.join(target_userspace, 'etc', 'yum.repos.d'))


def get_os_variant():
    """
    Retrieves the OS variant from the first matching OSReleaseFacts message. Returns an empty string otherwise.
    """
    for msg in api.consume(OSReleaseFacts):
        if msg.variant_id:
            return msg.variant_id
    return ''


def _get_product_certificate_path():
    """
    Retrieves the required / used product certificate for RHSM.
    """
    sys_var = get_os_variant()
    var_prodcert = {'server': '479.pem'}
    if sys_var not in var_prodcert:
        raise StopActorExecutionError(
            message=('Failed to to retrieve Product Cert file.'
                     'Product cert file not available for System Variant \'{}\'.'.format(sys_var))
        )

    return api.get_file_path(var_prodcert[sys_var])


def _create_target_userspace_directories(target_userspace):
    _logger().debug('Creating target userspace directories.')
    try:
        utils.makedirs(target_userspace)
        _logger().debug('Done creating target userspace directories.')
    except OSError:
        _logger().error(
            'Failed to create temporary target userspace directories %s', target_userspace, exc_info=True)
        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': 'Please ensure that {directory} is empty and modifiable.'.format(
                    directory=target_userspace)
            }
        )


def perform():
    packages = {'dnf'}
    for message in api.consume(RequiredTargetUserspacePackages):
        packages.update(message.packages)

    rhsm_info = next(api.consume(SourceRHSMInfo), None)
    if not rhsm_info and not rhsm.skip_rhsm():
        api.log.warn("Could not receive RHSM information - Is this system registered?")
        return

    prod_cert_path = _get_product_certificate_path()
    with overlaygen.create_source_overlay(
            mounts_dir=constants.MOUNTS_DIR,
            scratch_dir=constants.SCRATCH_DIR) as overlay:
        with overlay.nspawn() as context:
            with rhsm.switched_certificate(context, rhsm_info, prod_cert_path) as target_rhsm_info:
                _logger().debug("Target RHSM Info: SKUs: {skus} Repositories: {repos}".format(
                    repos=target_rhsm_info.enabled_repos,
                    skus=rhsm_info.attached_skus if rhsm_info else []
                ))
                target_repoids = rhsm.gather_target_repositories(target_rhsm_info)
                _logger().debug("Gathered target repositories: {}".format(', '.join(target_repoids)))
                prepare_target_userspace(context, constants.TARGET_USERSPACE, target_repoids, list(packages))
                _prep_repository_access(context, constants.TARGET_USERSPACE)
                dnfplugin.install(constants.TARGET_USERSPACE)
                rhsm.produce_used_target_repositories(target_repoids)
                api.produce(target_rhsm_info)
                api.produce(TargetUserSpaceInfo(
                    path=constants.TARGET_USERSPACE,
                    scratch=constants.SCRATCH_DIR,
                    mounts=constants.MOUNTS_DIR))
