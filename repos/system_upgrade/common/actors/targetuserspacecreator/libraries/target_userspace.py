from contextlib import contextmanager
import itertools
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor.constants import PERSISTENT_PACKAGE_CACHE_DIR
from leapp.libraries.common.config import get_env, version
from leapp.libraries.common import mounting, utils, rhsm
from leapp.libraries.stdlib import api, CalledProcessError, config, run


def _restore_persistent_package_cache(userspace_dir):
    if get_env('LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE', None) == '1':
        if os.path.exists(PERSISTENT_PACKAGE_CACHE_DIR):
            with mounting.NspawnActions(base_dir=userspace_dir) as target_context:
                target_context.copytree_to(PERSISTENT_PACKAGE_CACHE_DIR, '/var/cache/dnf')
    # We always want to remove the persistent cache here to unclutter the system
    run(['rm', '-rf', PERSISTENT_PACKAGE_CACHE_DIR])


def _backup_to_persistent_package_cache(userspace_dir):
    if get_env('LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE', None) == '1':
        # Clean up any dead bodies, just in case
        run(['rm', '-rf', PERSISTENT_PACKAGE_CACHE_DIR])
        if os.path.exists(os.path.join(userspace_dir, 'var', 'cache', 'dnf')):
            with mounting.NspawnActions(base_dir=userspace_dir) as target_context:
                target_context.copytree_from('/var/cache/dnf', PERSISTENT_PACKAGE_CACHE_DIR)


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


def _create_dnf_command_line(target_major_version, packages, enabled_repos):
    repos_opt = [['--enablerepo', repo] for repo in enabled_repos]
    repos_opt = list(itertools.chain(*repos_opt))

    command = [
        'dnf',
        'install',
        '-y',
        '--nogpgcheck',
        '--setopt=module_platform_id=platform:el{}'.format(target_major_version),
        '--setopt=keepcache=1',
        '--releasever', api.current_actor().configuration.version.target,
        '--installroot', '/el{}target'.format(target_major_version),
        '--disablerepo', '*'
    ]
    command.extend(repos_opt)
    command.extend(packages)
    if config.is_verbose():
        command.append('-v')
    if rhsm.skip_rhsm():
        command.extend(['--disableplugin', 'subscription-manager'])
    return command


@contextmanager
def _execution_context(context, userspace_dir, target_major_version):
    """
    Prepares and sets up the userspace directories for executing dnf
    """
    _backup_to_persistent_package_cache(userspace_dir)
    run(['rm', '-rf', userspace_dir])
    _create_target_userspace_directories(userspace_dir)
    with mounting.BindMount(
        source=userspace_dir,
        target=os.path.join(
            context.base_dir,
            'el{}target'.format(target_major_version)
        )
    ):
        _restore_persistent_package_cache(userspace_dir)
        yield


def prepare_target_userspace(context, userspace_dir, enabled_repos, packages):
    """
    Implement the creation of the target userspace.
    """
    target_major_version = version.get_target_major_version()
    with _execution_context(context, userspace_dir, target_major_version):
        cmd = _create_dnf_command_line(
                target_major_version=target_major_version,
                packages=packages,
                enabled_repos=enabled_repos
            )
        try:
            context.call(cmd, callback_raw=utils.logging_handler)
        except CalledProcessError as exc:
            raise StopActorExecutionError(
                message='Unable to install RHEL {} userspace packages.'.format(target_major_version),
                details={'details': str(exc), 'stderr': exc.stderr}
            )
