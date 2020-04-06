import itertools
import os

from leapp.exceptions import StopActorExecution, StopActorExecutionError
from leapp.libraries.actor import constants
from leapp.libraries.common import dnfplugin, mounting, overlaygen, rhsm, utils
from leapp.libraries.common.config import get_product_type, get_env
from leapp.libraries.stdlib import CalledProcessError, api, config, run
from leapp.models import (CustomTargetRepositoryFile, RequiredTargetUserspacePackages, RHSMInfo,
                          StorageInfo, TargetRepositories, TargetUserSpaceInfo,
                          UsedTargetRepositories, UsedTargetRepository,
                          XFSPresence)

PROD_CERTS_FOLDER = 'prod-certs'


def _check_deprecated_rhsm_skip():
    # we do not plan to cover this case by tests as it is purely
    # devel/testing stuff, that becomes deprecated now
    # just log the warning now (better than nothing?); deprecation process will
    # be specified in close future
    if get_env('LEAPP_DEVEL_SKIP_RHSM', '0') == '1':
        api.current_logger().warn(
            'The LEAPP_DEVEL_SKIP_RHSM has been deprecated. Use'
            ' LEAPP_NO_RHSM istead or use the --no-rhsm option for'
            ' leapp. as well custom repofile has not been defined.'
            ' Please read documentation about new "skip rhsm" solution.'
        )


class _InputData(object):
    def __init__(self):
        self._consume_data()

    def _consume_data(self):
        """
        Wrapper function to consume majority input data.

        It doesn't consume TargetRepositories, which are consumed in the
        own function.
        """
        self.packages = {'dnf'}
        for message in api.consume(RequiredTargetUserspacePackages):
            self.packages.update(message.packages)

        # Get the RHSM information (available repos, attached SKUs, etc.) of the source (RHEL 7) system
        self.rhsm_info = next(api.consume(RHSMInfo), None)
        if not self.rhsm_info and not rhsm.skip_rhsm():
            api.current_logger().warn('Could not receive RHSM information - Is this system registered?')
            raise StopActorExecution()
        if rhsm.skip_rhsm() and self.rhsm_info:
            # this should not happen. if so, raise an error as something in
            # other actors is wrong really
            raise StopActorExecutionError("RHSM is not handled but the RHSMInfo message has been produced.")

        # list comprehension needed on Py2

        self.custom_repofiles = list(api.consume(CustomTargetRepositoryFile))
        self.xfs_info = next(api.consume(XFSPresence), XFSPresence())
        self.storage_info = next(api.consume(StorageInfo), None)
        if not self.storage_info:
            raise StopActorExecutionError('No storage info available cannot proceed.')


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
        if rhsm.skip_rhsm():
            cmd += ['--disableplugin', 'subscription-manager']
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
    # FIXME: check that required repo IDs (baseos, appstream)
    # + or check that all required RHEL repo IDs are available.
    if not rhsm.skip_rhsm():
        # Get the RHSM repos available in the RHEL 8 container
        # TODO: very similar thing should happens for all other repofiles in container
        #
        available_repos = rhsm.get_available_repo_ids(context)
        if not available_repos or len(available_repos) < 2:
            raise StopActorExecutionError(
                message='Cannot find required basic RHEL 8 repositories.',
                details={
                    # FIXME: update the text - mention the possibility of custom repos
                    'hint': ('It is required to have RHEL repositories on the system'
                             ' provided by the subscription-manager unless the --no-rhsm'
                             ' options is specified. Possibly you'
                             ' are missing a valid SKU for the target system or network'
                             ' connection failed. Check whether your system is attached'
                             ' to a valid SKU providing RHEL 8 repositories.'
                             ' In case the Satellite is used, read the upgrade documentation'
                             ' to setup the satellite and the system properly.')
                }
            )
    else:
        available_repos = []

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
            # FIXME: this have to be done for the PR !!
            # # now it works well when the custom repofile is used, but
            # # we should require that all those repositories really exists
            # TODO: complete processing of custom repositories
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
                ' your current subscription is entitled to install the requested target version {version}.'
                ' In case the --no-rhsm option (or the LEAPP_NO_RHSM=1 environment variable is set)'
                ' ensure the custom repository file is provided regarding the documentation with'
                ' properly defined repositories.'
                ).format(version=api.current_actor().configuration.version.target)
            }
        )
    return target_repoids


def _install_custom_repofiles(context, custom_repofiles):
    """
    Install the required custom repository files into the container.

    The repostory files are copied from the host into the /etc/yum.repos.d
    directory into the container.

    :param context: the container where the repofiles should be copied
    :type context: mounting.IsolatedActions class
    :param custom_repofiles: list of custom repo files
    :type custom_repofiles: List(CustomTargetRepositoryFile)
    """
    for rfile in custom_repofiles:
        _dst_path = os.path.join('/etc/yum.repos.d', os.path.basename(rfile.file))
        context.copy_to(rfile.file, _dst_path)


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
    _install_custom_repofiles(context, indata.custom_repofiles)
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
    # NOTE: this one action is out of unit-tests completely; we do not use
    # in unit tests the LEAPP_DEVEL_SKIP_RHSM envar anymore
    _check_deprecated_rhsm_skip()

    indata = _InputData()
    prod_cert_path = _get_product_certificate_path()
    with overlaygen.create_source_overlay(
            mounts_dir=constants.MOUNTS_DIR,
            scratch_dir=constants.SCRATCH_DIR,
            storage_info=indata.storage_info,
            xfs_info=indata.xfs_info) as overlay:
        with overlay.nspawn() as context:
            target_repoids = _gather_target_repositories(context, indata, prod_cert_path)
            _create_target_userspace(context, indata.packages, target_repoids)
            api.produce(UsedTargetRepositories(
                repos=[UsedTargetRepository(repoid=repo) for repo in target_repoids]))
            api.produce(TargetUserSpaceInfo(
                path=constants.TARGET_USERSPACE,
                scratch=constants.SCRATCH_DIR,
                mounts=constants.MOUNTS_DIR))
