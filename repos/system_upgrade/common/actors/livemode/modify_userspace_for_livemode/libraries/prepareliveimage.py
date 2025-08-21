import errno
import grp
import os
import os.path

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import LiveImagePreparationInfo

LEAPP_UPGRADE_SERVICE_FILE = 'upgrade.service'
""" Service that executes the actual upgrade (/usr/bin/upgrade). """

LEAPP_CONSOLE_SERVICE_FILE = 'console.service'
""" Service that tails (tail -f) leapp logs and outputs them on tty1. """

LEAPP_STRACE_SERVICE_FILE = 'upgrade-strace.service'
""" Service that executes the upgrade while strace-ing the corresponding Leapp's process tree. """

SOURCE_ROOT_MOUNT_LOCATION = '/run/initramfs/live'
""" Controls where the source system's root will be mounted inside the upgrade image. """


def create_fstab_mounting_current_root_elsewhere(context, host_fstab):
    """
    Create a new /etc/fstab file that mounts source system filesystem to relative other mountpoint than /.

    The location of the source system's / will be mounted at SOURCE_ROO_MOUNT_LOCATION, and all other
    mountpoints present in source system's fstab will be made relative to SOURCE_ROOT_MOUNT_LOCATION.

    :returns: None
    :raises StopActorExecutionError: The upgrade is stopped if the new fstab could not be created.
    """

    live_fstab_lines = list()

    for fstab_entry in host_fstab:
        relative_root = SOURCE_ROOT_MOUNT_LOCATION

        if fstab_entry.fs_vfstype == 'swap':
            relative_root = '/'
        elif fstab_entry.fs_vfstype not in ('xfs', 'ext4', 'ext3', 'vfat'):
            msg = 'The following fstab entry is skipped and it will not be present in upgrade image\'s fstab entry: %s'
            api.current_logger().debug(msg, fstab_entry.fs_file)
            continue

        new_mountpoint = os.path.join(relative_root, fstab_entry.fs_file.lstrip('/'))

        entry = ' '.join([fstab_entry.fs_spec, new_mountpoint, fstab_entry.fs_vfstype, fstab_entry.fs_mntops,
                          fstab_entry.fs_freq, fstab_entry.fs_passno])

        live_fstab_lines.append(entry)

    live_fstab_content = '\n'.join(live_fstab_lines) + '\n'

    try:
        with context.open('/etc/fstab', 'w+') as upgrade_img_fstab:
            upgrade_img_fstab.write(live_fstab_content)
    except OSError as error:
        api.current_logger().error('Failed to create upgrade image\'s /etc/fstab. Error: %s', error)

        details = {'Problem': 'write to /etc/fstab failed.'}
        raise StopActorExecutionError('Cannot create upgrade image\'s /etc/fstab', details)


def create_symlink_from_sysroot_to_source_root_mountpoint(context):
    """
    Create a symlink from /sysroot to SOURCE_ROOT_MOUNT_LOCATION.

    The root (/) of the source system will be mounted at SOURCE_ROOT_MOUNT_LOCATION in the upgrade image,
    however, upgrade scripts expect the source system's root to be at /sysroot.

    :raises StopActorExecutionError: Failing to create a symlink leads to stopping the upgrade process as it
                                     is a critical step.
    """
    try:
        os.symlink(SOURCE_ROOT_MOUNT_LOCATION, context.full_path('/sysroot'))
    except OSError as err:
        api.current_logger().warning('Failed to create the /sysroot symlink. Full error: %s', err)
        raise StopActorExecutionError('Failed to create mountpoint symlink')


def setup_console(context):
    """
    Setup the console - upgrade logs on tty1 and tty2-tty4 will be standard terms (agetty).
    """
    api.current_logger().debug('Configuring the console')

    service_file = api.get_actor_file_path(LEAPP_CONSOLE_SERVICE_FILE)
    console_service_dest = os.path.join('/usr/lib/systemd/system/', LEAPP_CONSOLE_SERVICE_FILE)

    try:
        context.copy_to(service_file, console_service_dest)
    except OSError as error:
        api.current_logger().error(
            'Failed to copy the leapp\'s console service into the target userspace. Error: %s', error
        )
        details = {
            'Problem': 'Failed to copy leapp\'s console service into the upgrade image.'
        }
        raise StopActorExecutionError('Failed to set up upgrade image\'s console service', details=details)

    # Enable automatic spawning of virtual terminals to create automatically. When switching to a previously unused
    # VT, "autovt" services are created automatically (linked to getty by default). See man 5 logind.conf
    try:
        with context.open('/etc/systemd/logind.conf', 'a') as logind_conf:
            logind_conf.write('NAutoVTs=1\n')
    except OSError as error:
        msg = 'Failed to modify logind.conf to change the number of VTs created automatically. Full error: %s'
        api.current_logger().error(msg, error)

        problem_desc = (
            'Failed to modify upgrade image\'s logind.conf to specify the number of VTs created automatically'
        )
        details = {'Problem': problem_desc}
        raise StopActorExecutionError('Failed to setup console for the upgrade image.', details=details)

    tty_service_path_template = '/etc/systemd/system/getty.target.wants/getty@tty{tty_num}.service'
    console_enablement_link = os.path.join('/etc/systemd/system/multi-user.target.wants/', LEAPP_CONSOLE_SERVICE_FILE)

    try:
        # tty1 will be populated with leapp's logs
        tty1_service_symlink = tty_service_path_template.format(tty_num='1')
        if os.path.exists(tty1_service_symlink):
            context.remove(tty1_service_symlink)  # Will be used to output leapp there

        for i in range(2, 5):
            ttyi_service_path = context.full_path(tty_service_path_template.format(tty_num=i))
            os.symlink('/usr/lib/systemd/system/getty@.service', ttyi_service_path)

        os.symlink(console_service_dest, context.full_path(console_enablement_link))
    except OSError as error:
        api.current_logger().error('Failed to change how tty services are set up in the upgrade image. Error: %s',
                                   error)
        details = {'Problem': 'Failed to modify tty services in the upgrade image'}
        raise StopActorExecutionError('Failed to setup console for the upgrade image.', details=details)


def setup_upgrade_service(context):
    """
    Setup the systemd service that starts upgrade after reboot.

    The performed setup consists of:
    - install leapp_upgrade.sh as /usr/bin/upgrade
    - systemd symlink
    - install upgrade-strace.service

    :returns: None
    :raises StopActorExecutionError: Setting up upgrade service(s) is critical - failure in copying the required files
                                     or creating symlinks activating the services stops the upgrade.
    """
    api.current_logger().info('Configuring the upgrade.service')

    upgrade_service_path = api.get_actor_file_path(LEAPP_UPGRADE_SERVICE_FILE)
    do_upgrade_shellscript_path = api.get_actor_file_path('do-upgrade.sh')
    upgrade_strace_service_path = api.get_actor_file_path(LEAPP_STRACE_SERVICE_FILE)

    upgrade_service_dst_path = os.path.join('/usr/lib/systemd/system/', LEAPP_UPGRADE_SERVICE_FILE)
    strace_service_dst_path = os.path.join('/usr/lib/systemd/system/', LEAPP_STRACE_SERVICE_FILE)

    try:
        context.copy_to(upgrade_service_path, upgrade_service_dst_path)
        context.copy_to(upgrade_strace_service_path, strace_service_dst_path)
        context.copy_to(do_upgrade_shellscript_path, '/usr/bin/upgrade')
    except OSError as err:
        details = {
            'Problem': 'copying leapp_upgrade.service and leapp_upgrade.sh to the target userspace failed.',
            'err': str(err)
        }
        raise StopActorExecutionError('Cannot copy the leapp_upgrade service files', details=details)

    # Enable Leapp's services by adding them as dependency to multi-user.target.wants

    services_to_enable = [upgrade_service_dst_path, strace_service_dst_path]
    symlink_dest_dir = '/etc/systemd/system/multi-user.target.wants/'

    for service_path in services_to_enable:
        service_file = os.path.basename(service_path)
        symlink_dst = os.path.join(symlink_dest_dir, service_file)
        try:
            os.symlink(service_path, context.full_path(symlink_dst))
        except OSError as error:
            api.current_logger().error('Failed to create a symlink enabling leapp\'s upgrade service (%s). Error %s',
                                       service_path, error)

            details = {'Problem': 'Failed to enable leapp\'s upgrade service (upgrade.service)'}
            raise StopActorExecutionError('Cannot enable the upgrade.service', details=details)


def make_root_account_passwordless(context):
    """
    Make root account passwordless.

    Modify /etc/passwd found in the upgrade image, removing root's password.

    :returns: Noting.
    :raises StopActorExecutionError: The upgrade is stopped if the user requests upgrade root account to be
                                     passwordless, however, the corresponding modifications could not be performed.
    """
    target_userspace_passwd_path = context.full_path('/etc/passwd')

    if not os.path.exists(target_userspace_passwd_path):
        api.current_logger().warning('Target userspace is lacking /etc/passwd; cannot setup passwordless root.')
        return

    try:
        with context.open('/etc/passwd') as f:
            passwd = f.readlines()
    except OSError:
        msg = 'Failed to open target userspace /etc/passwd for reading; passwordless root will not be set up.'
        api.current_logger().error(msg)
        details = {'Problem': 'Failed to open target userspace /etc/passwd for reading'}
        raise StopActorExecutionError(
            'Could not set up passwordless root login for the upgrade environment.',
            details=details
        )

    new_passwd_lines = []
    found_root_entry = False
    for entry in passwd:
        if entry.startswith('root:'):
            found_root_entry = True

            root_fields = entry.split(':')
            root_fields[1] = ''
            entry = ':'.join(root_fields)

        new_passwd_lines.append(entry)

    if not found_root_entry:
        msg = 'Failed to set up a passwordless root login in the target userspace - there is no root user entry.'
        api.current_logger().warning(msg)
        details = {'Problem': 'There is no root user entry in target userspace\'s /etc/passwd'}
        raise StopActorExecutionError(
            'Could not set up passwordless root login for the upgrade environment.',
            details=details
        )

    try:
        with context.open('/etc/passwd', 'w+') as passwd_file:
            passwd_contents = ''.join(new_passwd_lines)
            passwd_file.write(passwd_contents)
    except OSError:
        api.current_logger().warning('Failed to write new contents into target userspace /etc/passwd.')
        raise StopActorExecutionError(
            'Could not set up passwordless root login for the upgrade environment.',
            details={'Problem': 'Filed to write /etc/passwd for the upgrade environment'}
        )


def enable_dbus(context):
    """
    Enable dbus-daemon into the target userspace
    Looks like it's not enabled by default when installing into a container.
    """
    dbus_daemon_service = '/usr/lib/systemd/system/dbus-daemon.service'

    links = ['/etc/systemd/system/multi-user.target.wants/dbus-daemon.service',
             '/etc/systemd/system/dbus.service',
             '/etc/systemd/system/messagebus.service']

    api.current_logger().info(('Enabling dbus services. Leapp will attempt to create the following '
                               'symlinks: {0}, all pointing to {1}').format(', '.join(links),
                                                                            dbus_daemon_service))

    for link in links:
        api.current_logger().debug('Creating symlink at {0} that points to {1}'.format(link, dbus_daemon_service))
        try:
            os.symlink('/usr/lib/systemd/system/dbus-daemon.service', context.full_path(link))
        except OSError as err:
            if err.errno == errno.EEXIST:
                # @Note: We are not catching FileExistsError because of python2 (there is no such error class)
                # We are performing installations within container, so the systemd symlinks that are created
                # during installation should have correct destination
                api.current_logger().debug(
                    'A file already exists at {0}, assuming it is a symlink with a correct content.'
                )
                continue

            details = {'Problem': 'An error occurred while creating the systemd symlink', 'source_error': str(err)}
            raise StopActorExecutionError('Cannot enable the dbus services', details=details)


def setup_network(context):
    """
    Setup network for the livemode image.

    Copy ifcfg files and NetworkManager's system connections into the live image.
    :returns: None
    :raises StopActorExecutionError: The exception is raised when failing to copy the configuration
                                     files into the livemode image.
    """
    # TODO(mhecko): implementation here is incomplete
    # ideally we'd need to run 'nmcli con migrate' for the live mode.
    if get_target_major_version() < "9":
        return  # 8>9 only

    network_scripts_path = '/etc/sysconfig/network-scripts'
    ifcfgs = [ifcfg for ifcfg in os.listdir(network_scripts_path) if ifcfg.startswith('ifcfg-')]

    network_manager_conns_path = '/etc/NetworkManager/system-connections'
    conns = os.listdir(network_manager_conns_path)

    try:
        if ifcfgs:
            context.makedirs(network_scripts_path, exists_ok=True)
        for ifcfg in ifcfgs:
            ifcfg_fullpath = os.path.join(network_scripts_path, ifcfg)
            context.copy_to(ifcfg_fullpath, ifcfg_fullpath)

        if conns:
            context.makedirs(network_manager_conns_path, exists_ok=True)
        for nm_conn in conns:
            nm_conn_fullpath = os.path.join(network_manager_conns_path, nm_conn)
            context.copy_to(nm_conn_fullpath, nm_conn_fullpath)
    except OSError as error:
        api.current_logger().error('Failed to setup network connections for the upgrade live image. Error: %s', error)
        details = {'Problem': str(error)}
        raise StopActorExecutionError('Failed to setup network connections for the upgrade live image.',
                                      details=details)


def setup_sshd(context, authorized_keys):
    """
    Setup a temporary ssh server with /root/.ssh/authorized_keys

    :param NspawnActions context: Context (target userspace) abstracting the root structure which will
                                  become the upgrade image.
    :param authorized_keys: Path to a file containing a list of (public) ssh keys that can authenticate
                            to the upgrade sshd server.
    :returns: None
    :raises StopActorExecutionError: The exception is raised when the sshd could not be set up.
    """
    api.current_logger().warning('Preparing temporary sshd for live mode')

    system_ssh_config_dir = '/etc/ssh'
    try:
        sshd_config = os.listdir(system_ssh_config_dir)
        hostkeys = [key for key in sshd_config if key.startswith('ssh_key_')]
        public = [key for key in hostkeys if key.endswith('.pub')]
        for key in hostkeys:
            key_path = os.path.join(system_ssh_config_dir, key)

            if key in public:
                access_rights = 0o644
                group = 'root'
            else:
                access_rights = 0o640
                group = 'ssh_keys'

            context.copy_to(key_path, system_ssh_config_dir)

            key_guest_path = context.full_path(key_path)
            os.chmod(key_guest_path, access_rights)
            os.chown(key_guest_path, uid=0, gid=grp.getgrnam(group).gr_gid)
    except OSError as error:
        api.current_logger().error('Failed to set up SSH keys from system\'s default location. Error: %s', error)
        raise StopActorExecutionError(
            'Failed to set up SSH keys from system\'s default location for the upgrade image.'
        )

    root_authorized_keys_path = '/root/.ssh/authorized_keys'
    try:
        context.makedirs(os.path.dirname(root_authorized_keys_path))
        context.copy_to(authorized_keys, root_authorized_keys_path)
        os.chmod(context.full_path(root_authorized_keys_path), 0o600)
        os.chmod(context.full_path('/root/.ssh'), 0o700)
    except OSError as error:
        api.current_logger().error('Failed to set up /root/.ssh/authorized_keys. Error: %s', error)
        details = {'Problem': 'Failed to set up /root/.ssh/authorized_keys. Error: {0}'.format(error)}
        raise StopActorExecutionError('Failed to set up SSH access for the upgrade image.', details=details)

    sshd_service_activation_link_dst = context.full_path('/etc/systemd/system/multi-user.target.wants/sshd.service')
    if not os.path.exists(sshd_service_activation_link_dst):
        try:
            os.symlink('/usr/lib/systemd/system/sshd.service', sshd_service_activation_link_dst)
        except OSError as error:
            api.current_logger().error(
                'Failed to enable the sshd service in the upgrade image (failed to create a symlink). Full error: %s',
                error
            )

# stolen from upgradeinitramfsgenerator.py
def _get_target_kernel_version(context):
    """
    Get the version of the most recent kernel version within the container.
    """
    try:
        results = context.call(['rpm', '-qa', 'kernel-core'], split=True)['stdout']

    except CalledProcessError as error:
        problem = 'Could not query the target userspace kernel version through rpm. Full error: {0}'.format(error)
        raise StopActorExecutionError(
            'Cannot get the version of the installed kernel.',
            details={'Problem': problem})

    if len(results) > 1:
        raise StopActorExecutionError(
            'Cannot detect the version of the target userspace kernel.',
            details={'Problem': 'Detected unexpectedly multiple kernels inside target userspace container.'})
    if not results:
        raise StopActorExecutionError(
            'Cannot detect the version of the target userspace kernel.',
            details={'Problem': 'An rpm query for the available kernels did not produce any results.'})

    kernel_version = '-'.join(results[0].rsplit("-", 2)[-2:])
    api.current_logger().debug('Detected kernel version inside container: {}.'.format(kernel_version))

    return kernel_version


def fakerootfs():
    """
    Create the FAKEROOTFS_FILE with source system's kernel cmdline.

    The list of parameters is used after the reboot to replace live system's `root=` parameter with the original one
    so that kernel-core RPM installs properly.

    :returns: None
    :raises StopActorExecutionError: The error is raised when the FAKEROOTFS_FILE cannot be created.
    """
    FAKEROOTFS_FILE = '/var/lib/leapp/.fakerootfs'
    with open('/proc/cmdline') as f:
        all_args = f.read().split(' ')

    args_to_write = (arg.strip() for arg in all_args if not arg.startswith('BOOT_IMAGE'))

    try:
        with open(FAKEROOTFS_FILE, 'w+') as f:
            f.write(' '.join(args_to_write))
    except OSError as error:
        api.current_logger().error('Failed to create the FAKEROOTFS_FILE. Full error: %s', error)
        raise StopActorExecutionError(
            'Cannot prepare the kernel cmdline workaround.',
            details={'Problem': 'Cannot write {0}'.format(FAKEROOTFS_FILE)}
        )


def create_etc_issue(context, stop_upgrade_on_failure=False):
    """
    Create /etc/issue warning the user about upgrade being in-progress.
    """
    try:
        msg = ('\n\n\n'
               '============================================================\n'
               '         LEAPP LIVE UPGRADE MODE - *UNSUPPORTED*\n'
               '============================================================\n'
               '      DO NOT REBOOT until the upgrade is finished.\n'
               '      Upgrade logs are sent on tty1 (Ctrl+Alt+F1)\n'
               '============================================================\n'
               ' It will automatically reboot unless you touch this file:\n'
               '   # touch /sysroot/.noreboot\n'
               '\n'
               ' If upgrade.autostart=0 is set, run an upgrade manually:\n'
               '   # upgrade |& tee /sysroot/var/log/leapp/leapp-upgrade.log\n'
               '\n'
               ' Log in as root, without password.\n'
               '\n\n')

        with context.open('/etc/issue', 'w+') as f:
            f.write(msg)
        with context.open('/etc/motd', 'w+') as f:
            f.write(msg)
    except OSError as error:
        api.current_logger().warning('Cannot write /etc/issue. Full error: %s', error)
        if stop_upgrade_on_failure:
            raise StopActorExecutionError('Failed to set up /etc/issue informing the user about pending upgrade.')


def modify_userspace_as_configured(userspace_info, storage, livemode_config):
    """
    Prepare the (minimal) target RHEL userspace to be squashed into an image.

    The following preparation steps are performed:
    - upgrade services and scripts are copied into the image and enabled
    - console is set up to display leapp's logs on tty0
    - sshd is set up (if configured)
    - kernel and initramfs is generated
    - a new /etc/fstab is generating, mounting / of the source system somewhere else
    - /etc/issue is created, informing user about the ongoing upgrade
    - network manager is set up
    """
    if not livemode_config or not livemode_config.is_enabled:
        return

    setup_info = LiveImagePreparationInfo()
    with mounting.NspawnActions(base_dir=userspace_info.path) as context:
        # Perform all mounts that are required to make the userspace functional, and then
        # create an Nspawn context inside the userspace

        # Non-configurable modifications:
        setup_upgrade_service(context)
        setup_console(context)
        create_fstab_mounting_current_root_elsewhere(context, storage.fstab)
        create_symlink_from_sysroot_to_source_root_mountpoint(context)
        create_etc_issue(context)
        enable_dbus(context)

        # Configurable modifications:

        if livemode_config.setup_opensshd_with_auth_keys:
            setup_sshd(context, livemode_config.setup_opensshd_with_auth_keys)
            setup_info.has_sshd = True

        if livemode_config.setup_passwordless_root:
            make_root_account_passwordless(context)
            setup_info.has_passwordless_root = True

        if livemode_config.setup_network_manager:
            setup_network(context)
            setup_info.has_network_set_up = True

    fakerootfs()  # Workaround to hide the squashfs root arg in /proc/cmdline

    api.produce(setup_info)
