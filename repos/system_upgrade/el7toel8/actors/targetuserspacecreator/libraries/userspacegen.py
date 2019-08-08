import itertools
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import constants
from leapp.libraries.common import dnfplugin, mounting, overlaygen, rhsm, utils
from leapp.libraries.stdlib import api, run
from leapp.models import (IPUConfig, RequiredTargetUserspacePackages, SourceRHSMInfo, TargetRepositories,
                          TargetUserSpaceInfo, UsedTargetRepositories, UsedTargetRepository, XFSPresence)


PROD_CERTS_FOLDER = 'prod-certs'


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


def _get_product_certificate_path():
    """
    Retrieves the required / used product certificate for RHSM.
    """
    config = next(api.consume(IPUConfig), None)
    variant = config.os_release.variant_id
    architecture = config.architecture
    tgt_version = config.version.target
    # TODO: so far only base channel is available in rhel8
    tgt_channel = 'base'
    certs_folder = api.get_common_folder_path(PROD_CERTS_FOLDER)

    prod_certs = {
        'server': {
            'x86_64': {
                'base': '479.pem',
                # 'EUS': TBD
            },
            'aarch64': {
                'base': '419.pem',
                # 'EUS': TBD
            },
            'ppc64le': {
                'base': '279.pem',
                # 'EUS': TBD
            },
            's390x': {
                'base': '72.pem',
                # 'EUS': TBD
            }
        }
    }

    try:
        cert = prod_certs[variant][architecture][tgt_channel]
    except KeyError as e:
        raise StopActorExecutionError(message=('Failed to determine what certificate to use for {}.'.format(e)))

    return os.path.join(certs_folder, tgt_version, cert)


def _create_target_userspace_directories(target_userspace):
    api.current_logger().debug('Creating target userspace directories.')
    try:
        utils.makedirs(target_userspace)
        api.current_logger().debug('Done creating target userspace directories.')
    except OSError:
        api.current_logger().error(
            'Failed to create temporary target userspace directories %s', target_userspace, exc_info=True)
        # This is an attempt for giving the user a chance to resolve it on their own
        raise StopActorExecutionError(
            message='Failed to prepare environment for package download while creating directories.',
            details={
                'hint': 'Please ensure that {directory} is empty and modifiable.'.format(directory=target_userspace)
            }
        )


def gather_target_repositories(target_rhsm_info):
    """
    Performs basic checks on requirements for RHSM repositories and returns the list of target repository ids to use
    during the upgrade.
    """
    # FIXME: check that required repo IDs (baseos, appstream)
    # + or check that all required RHEL repo IDs are available.
    if not rhsm.skip_rhsm():
        if not target_rhsm_info.available_repos or len(target_rhsm_info.available_repos) < 2:
            raise StopActorExecutionError(
                message='Cannot find required basic RHEL repositories.',
                details={
                    'hint': ('It is required to have RHEL repository on the system'
                             ' provided by the subscription-manager. Possibly you'
                             ' are missing a valid SKU for the target system or network'
                             ' connection failed. Check whether your system is attached'
                             ' to the valid SKU providing target repositories.')
                }
            )

    target_repoids = []
    for target_repo in api.consume(TargetRepositories):
        for rhel_repo in target_repo.rhel_repos:
            if rhel_repo.repoid in target_rhsm_info.available_repos:
                target_repoids.append(rhel_repo.repoid)
        for custom_repo in target_repo.custom_repos:
            # TODO: complete processing of custom repositories
            # HINT: now it will work only for custom repos that exist
            # + already on the system in a repo file
            # TODO: should check available_target_repoids + additional custom repos
            # + outside of rhsm..
            # #if custom_repo.repoid in available_target_repoids:
            target_repoids.append(custom_repo.repoid)
    return target_repoids


def perform():
    packages = {'dnf'}
    for message in api.consume(RequiredTargetUserspacePackages):
        packages.update(message.packages)

    rhsm_info = next(api.consume(SourceRHSMInfo), None)
    if not rhsm_info and not rhsm.skip_rhsm():
        api.current_logger().warn("Could not receive RHSM information - Is this system registered?")
        return

    presence = next(api.consume(XFSPresence), XFSPresence())
    xfs_present = presence.present and presence.without_ftype

    prod_cert_path = _get_product_certificate_path()
    with overlaygen.create_source_overlay(
            mounts_dir=constants.MOUNTS_DIR,
            scratch_dir=constants.SCRATCH_DIR,
            xfs_present=xfs_present) as overlay:
        with overlay.nspawn() as context:
            target_version = api.current_actor().configuration.version.target
            with rhsm.switched_certificate(context, rhsm_info, prod_cert_path, target_version) as target_rhsm_info:
                api.current_logger().debug("Target RHSM Info: SKUs: {skus} Repositories: {repos}".format(
                    repos=target_rhsm_info.enabled_repos,
                    skus=rhsm_info.attached_skus if rhsm_info else []
                ))
                target_repoids = gather_target_repositories(target_rhsm_info)
                api.current_logger().debug("Gathered target repositories: {}".format(', '.join(target_repoids)))
                if not target_repoids:
                    raise StopActorExecutionError(
                        message='There are no enabled target repositories for the upgrade process to proceed.',
                        details={'hint': (
                            'Ensure your system is correctly registered with the subscription manager and that'
                            ' your current subscription is entitled to install the requested target version {version}'
                            ).format(version=api.current_actor().configuration.version.target)
                        }
                    )
                prepare_target_userspace(context, constants.TARGET_USERSPACE, target_repoids, list(packages))
                _prep_repository_access(context, constants.TARGET_USERSPACE)
                dnfplugin.install(constants.TARGET_USERSPACE)
                api.produce(UsedTargetRepositories(
                    repos=[UsedTargetRepository(repoid=repo) for repo in target_repoids]))
                api.produce(target_rhsm_info)
                api.produce(TargetUserSpaceInfo(
                    path=constants.TARGET_USERSPACE,
                    scratch=constants.SCRATCH_DIR,
                    mounts=constants.MOUNTS_DIR))
