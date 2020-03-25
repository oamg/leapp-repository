import itertools
import os

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import constants
from leapp.libraries.common import dnfplugin, mounting, overlaygen, rhsm, utils
from leapp.libraries.common.config import get_product_type
from leapp.libraries.stdlib import CalledProcessError, api, config, run
from leapp.models import (RequiredTargetUserspacePackages, RHSMInfo,
                          StorageInfo, TargetRepositories, TargetUserSpaceInfo,
                          UsedTargetRepositories, UsedTargetRepository,
                          XFSPresence)

PROD_CERTS_FOLDER = 'prod-certs'


def prepare_target_userspace(context, userspace_dir, enabled_repos, packages):
    """
    Implement the creation of the target userspace.
    """
    run(['rm', '-rf', userspace_dir])
    _create_target_userspace_directories(userspace_dir)
    with mounting.BindMount(source=userspace_dir, target=os.path.join(context.base_dir, 'el8target')):
        repos_opt = [['--enablerepo', repo] for repo in enabled_repos]
        repos_opt = list(itertools.chain(*repos_opt))
        cmd = ['dnf',
               'install',
               '-y',
               '--nogpgcheck',
               '--setopt=module_platform_id=platform:el8',
               '--setopt=keepcache=1',
               '--releasever', api.current_actor().configuration.version.target,
               '--installroot', '/el8target',
               '--disablerepo', '*'
               ] + repos_opt + packages
        if config.is_verbose():
            cmd.append('-v')
        try:
            context.call(cmd, callback_raw=utils.logging_handler)
        except CalledProcessError as exc:
            raise StopActorExecutionError(
                message='Unable to install RHEL 8 userspace packages.',
                details={'details': str(exc), 'stderr': exc.stderr}
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
    Retrieve the required / used product certificate for RHSM.
    """
    architecture = api.current_actor().configuration.architecture
    target_version = api.current_actor().configuration.version.target
    target_product_type = get_product_type('target')
    certs_dir = api.get_common_folder_path(PROD_CERTS_FOLDER)

    # TODO: do we need EUS/... here or is it ga one enough to get eus repos?
    prod_certs = {
        'x86_64': {
            'ga': '479.pem',
            'beta': '486.pem',
            'htb': '230.pem',
        },
        'aarch64': {
            'ga': '419.pem',
            'beta': '363.pem',
            'htb': '489.pem',
        },
        'ppc64le': {
            'ga': '279.pem',
            'beta': '362.pem',
            'htb': '233.pem',
        },
        's390x': {
            'ga': '72.pem',
            'beta': '433.pem',
            'htb': '232.pem',
        }
    }

    try:
        cert = prod_certs[architecture][target_product_type]
    except KeyError as e:
        raise StopActorExecutionError(message=('Failed to determine what certificate to use for {}.'.format(e)))

    cert_path = os.path.join(certs_dir, target_version, cert)
    if not os.path.isfile(cert_path):
        details = {'missing certificate': cert, 'path': cert_path}
        if target_product_type != 'ga':
            details['hint'] = (
                'You chose to upgrade to beta or htb system but probably'
                ' chose version for which beta/htb certificates are not'
                ' attached (e.g. because the GA has been released already).'
                ' Set the target os version for which the {} certificate'
                ' is provided using the LEAPP_DEVEL_TARGET_RELEASE envar.'
                .format(cert)
            )
            details['search cmd'] = 'find {} | grep {}'.format(certs_dir, cert)
        raise StopActorExecutionError(
            message='Cannot find the product certificate file for the chosen target system.',
            details=details
        )
    return cert_path


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


def gather_target_repositories(context):
    """
    Perform basic checks on requirements for RHSM repositories and return the list of target repository ids to use
    during the upgrade.

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :return: List of target system repoids
    :rtype: List(string)
    """
    # Get the RHSM repos available in the RHEL 8 container
    # FIXME: this cannot happen with custom --no-rhsm setup
    available_repos = rhsm.get_available_repo_ids(context)

    # FIXME: check that required repo IDs (baseos, appstream)
    # + or check that all required RHEL repo IDs are available.
    if not rhsm.skip_rhsm():
        if not available_repos or len(available_repos) < 2:
            raise StopActorExecutionError(
                message='Cannot find required basic RHEL 8 repositories.',
                details={
                    'hint': ('It is required to have RHEL repositories on the system'
                             ' provided by the subscription-manager. Possibly you'
                             ' are missing a valid SKU for the target system or network'
                             ' connection failed. Check whether your system is attached'
                             ' to a valid SKU providing RHEL 8 repositories.')
                }
            )

    target_repoids = []
    for target_repo in api.consume(TargetRepositories):
        for rhel_repo in target_repo.rhel_repos:
            if rhel_repo.repoid in available_repos:
                target_repoids.append(rhel_repo.repoid)
            else:
                # TODO: We shall report that the RHEL repos that we deem necessary for the upgrade are not available.
                # The StopActorExecutionError called above might be moved here.
                pass
        for custom_repo in target_repo.custom_repos:
            # TODO: complete processing of custom repositories
            # HINT: now it will work only for custom repos that exist
            # + already on the system in a repo file
            # TODO: should check available_target_repoids + additional custom repos
            # + outside of rhsm..
            # #if custom_repo.repoid in available_target_repoids:
            target_repoids.append(custom_repo.repoid)
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
    return target_repoids


def _consume_data():
    """Wrapper function to consume all input data."""
    packages = {'dnf'}
    for message in api.consume(RequiredTargetUserspacePackages):
        packages.update(message.packages)

    # Get the RHSM information (available repos, attached SKUs, etc.) of the source (RHEL 7) system
    rhsm_info = next(api.consume(RHSMInfo), None)
    if not rhsm_info and not rhsm.skip_rhsm():
        api.current_logger().warn('Could not receive RHSM information - Is this system registered?')
        raise StopActorExecution()

    xfs_info = next(api.consume(XFSPresence), XFSPresence())
    storage_info = next(api.consume(StorageInfo), None)
    if not storage_info:
        raise StopActorExecutionError('No storage info available cannot proceed.')
    return packages, rhsm_info, xfs_info, storage_info


def _gather_target_repositories(context, rhsm_info, prod_cert_path):
    """
    This is wrapper function to gather the target repoids.

    Probably the function could be partially merged into gather_target_repositories
    and this could be really just wrapper with the switch of certificates.
    I am keeping that for now as it is as interim step.
    """
    rhsm.set_container_mode(context)
    rhsm.switch_certificate(context, rhsm_info, prod_cert_path)
    return gather_target_repositories(context)


def _create_target_userspace(context, packages, target_repoids):
    """Create the target userspace."""
    prepare_target_userspace(context, constants.TARGET_USERSPACE, target_repoids, list(packages))
    _prep_repository_access(context, constants.TARGET_USERSPACE)
    dnfplugin.install(constants.TARGET_USERSPACE)
    # and do not forget to set the rhsm into the container mode again
    with mounting.NspawnActions(constants.TARGET_USERSPACE) as target_context:
        rhsm.set_container_mode(target_context)


def perform():
    packages, rhsm_info, xfs_info, storage_info = _consume_data()
    prod_cert_path = _get_product_certificate_path()
    with overlaygen.create_source_overlay(
            mounts_dir=constants.MOUNTS_DIR,
            scratch_dir=constants.SCRATCH_DIR,
            storage_info=storage_info,
            xfs_info=xfs_info) as overlay:
        with overlay.nspawn() as context:
            target_repoids = _gather_target_repositories(context, rhsm_info, prod_cert_path)
            _create_target_userspace(context, packages, target_repoids)
            api.produce(UsedTargetRepositories(
                repos=[UsedTargetRepository(repoid=repo) for repo in target_repoids]))
            api.produce(TargetUserSpaceInfo(
                path=constants.TARGET_USERSPACE,
                scratch=constants.SCRATCH_DIR,
                mounts=constants.MOUNTS_DIR))
