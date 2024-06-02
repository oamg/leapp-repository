import os
import os.path
import grp
import shutil
import subprocess
from distutils.version import LooseVersion

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import PrepareLiveImageTasks

LEAPP_UPGRADE_SERVICE_FILE = 'upgrade.service'
LEAPP_CONSOLE_SERVICE_FILE = 'console.service'


def configure_fstab(context, host_fstab):
    """
    Prepend fstab mount points by /run/initramfs/live
    instead of /sysroot
    """
    live_fstab = list()

    for fs in host_fstab:
        prepend = '/run/initramfs/live'
        if fs.fs_vfstype == 'swap':
            prepend = ''
        if fs.fs_vfstype not in ('xfs', 'ext4', 'ext3', 'vfat'):
            continue
        ent = ' '.join([fs.fs_spec, prepend + fs.fs_file.rstrip('/'),
                        fs.fs_vfstype, fs.fs_mntops, fs.fs_freq, fs.fs_passno])
        live_fstab.append(ent)

    try:
        with context.open('/etc/fstab', 'w+') as f:
            f.write('\n'.join(live_fstab)+'\n')
    except:
        raise StopActorExecutionError(
            'Cannot configure fstab for live mode',
            details={'Problem': 'write to /etc/fstab failed.'})

    return True


def create_mountpoint(context):
    """
    Create a symlink from /sysroot to the /run/initramfs/live mount point
    """
    try:
        os.symlink('/run/initramfs/live', context.full_path('/sysroot'))
    except:
        api.current_logger().warning('Cannot create the /sysroot symlink')
        return False
    return True


def setup_console(context):
    """
    Setup the console:
    we do want upgrade logs on tty1 and tty2-tty4 as standard terms (agetty)
    """
    api.current_logger().info('Configuring the console')

    service_file = api.get_actor_file_path(LEAPP_CONSOLE_SERVICE_FILE)
    console_service = '/usr/lib/systemd/system/%s' % LEAPP_CONSOLE_SERVICE_FILE

    try:
        context.copy_to(service_file, console_service)
    except:
        api.current_logger().warning('Cannot configure the console')

    try:
        with context.open('/etc/systemd/logind.conf', 'a') as f:
            f.write('NAutoVTs=1\n')
    except:
        api.current_logger().warning('Cannot configure the console')
        return False

    tty = '/etc/systemd/system/getty.target.wants/getty@tty%s.service'
    lnk = '/etc/systemd/system/multi-user.target.wants/%s' \
            % LEAPP_CONSOLE_SERVICE_FILE
    try:
        context.remove(tty % 1)
        for i in range(2, 5):
            os.symlink('/usr/lib/systemd/system/getty@.service',
                context.full_path(tty % i))
        os.symlink(console_service, context.full_path(lnk))
    except:
        api.current_logger().warning('Cannot configure the console')
        return False

    return True


def setup_upgrade_service(context):
    """
    Setup the upgrade.service + leapp_upgrade.sh + systemd symlink
    """
    api.current_logger().info('Configuring the upgrade.service')

    service_file = api.get_actor_file_path(LEAPP_UPGRADE_SERVICE_FILE)
    service_path = os.path.dirname(service_file)
    upgrade_service = '/usr/lib/systemd/system/%s' % LEAPP_UPGRADE_SERVICE_FILE

    try:
        context.copy_to(service_file, upgrade_service)
        context.copy_to('%s/do-upgrade.sh' % service_path, '/usr/bin/upgrade')
        context.copy_to('%s/upgrade-strace.service' % service_path,
                        '/usr/lib/systemd/system/upgrade-strace.service')
    except :
        raise StopActorExecutionError(
            'Cannot copy the leapp_upgrade service files',
            details={'Problem': 'copying leapp_upgrade.service and '
                     'leapp_upgrade.sh to the target userspace failed.'})

    lnk1 = '/etc/systemd/system/multi-user.target.wants/%s' \
            % LEAPP_UPGRADE_SERVICE_FILE
    lnk2 = '/etc/systemd/system/multi-user.target.wants/upgrade-strace.service'
    try:
        os.symlink(upgrade_service, context.full_path(lnk1))
        os.symlink('/usr/lib/systemd/system/upgrade-strace.service',
            context.full_path(lnk2))
    except:
        raise StopActorExecutionError(
            'Cannot enable the upgrade.service',
            details={'Problem':
                     'An error occurred while creating the systemd symlink'})

    return True


def setup_root_account(context):
    """
    Disable password for the live root account
    """
    data = []

    try:
        with context.open('/etc/passwd') as f:
            passwd = f.readlines()
    except:
        api.current_logger().warning('no /etc/passwd file, no login.')
        return False

    for entry in passwd:
        new = entry
        if entry.startswith('root:x:'):
            new = entry.replace('root:x:', 'root::')
        data.append(new)

    try:
        with context.open('/etc/passwd', 'w+') as f:
            f.write(''.join(data))
    except:
        api.current_logger().warning('Cannot setup root login for live mode.')
        return False

    return True


def enable_dbus(context):
    """
    Enable dbus-daemon into the target userspace
    Looks like it's not enabled by default when installing into a container.
    """
    api.current_logger().info('Configuring the dbus services')

    upgrade_service = '/usr/lib/systemd/system/%s' % LEAPP_UPGRADE_SERVICE_FILE

    links = ['/etc/systemd/system/multi-user.target.wants/dbus-daemon.service',
             '/etc/systemd/system/dbus.service',
             '/etc/systemd/system/messagebus.service']
    try:
        for link in links:
            os.symlink('/usr/lib/systemd/system/dbus-daemon.service',
                context.full_path(link))
    except:
        raise StopActorExecutionError(
            'Cannot enable the dbus services',
            details={'Problem':
                     'An error occurred while creating the systemd symlink'})


def setup_nm(context, enable_nm):
    """
    Copy ifcfg files and nm's system connections
    """
    # TODO implementation here is uncomplete...
    # ideally we'd need to run nmcli con migrate for the live mode.
    if not enable_nm or get_target_major_version() < "9":
        return  # 8>9 only

    nsd = '/etc/sysconfig/network-scripts'
    ifcfgs = [ifcfg for ifcfg in os.listdir(nsd) if ifcfg.startswith('ifcfg-')]

    nmd = '/etc/NetworkManager/system-connections'
    conns = [conn for conn in os.listdir(nmd)]

    try:
        for ifcfg in ifcfgs:
            context.copy_to('{}/{}'.format(nsd, ifcfg))
        for conn in conns:
            context.copy_to('{}/{}'.format(nsd, conn))
    except:
        api.current_logger().warning('Cannot configure NM for live mode.')


def setup_sshd(context, authorized_keys):
    """
    Setup a temporary ssh server with /root/.ssh/authorized_keys
    """
    api.current_logger().warning('Preparing temporary sshd for live mode')

    try:
        ssh_dir = '/etc/ssh'
        sshd_config = os.listdir(ssh_dir)
        hostkeys = [key for key in sshd_config if key.startswith('ssh_key_')]
        public = [key for key in hostkeys if key.endswith('.pub')]
        for key in hostkeys:
            chmod = 0o644 if key in public else 0o640
            group = 'root' if key in public else 'ssh_keys'
            key_path = '{}/{}'.format(ssh_dir, key)
            context.copy_to(key_path)
            os.chmod(key_path, chmod)
            os.chown(key_path, 0, grp.getgrnam(group).gr_gid)
    except:
        api.current_logger().warning('Cannot setup ssh hostkeys')

    try:
        context.makedirs(os.path.dirname(authorized_keys))
        context.copy_to(authorized_keys, '/root/.ssh/authorized_keys')
        os.chmod(context.full_path('/root/.ssh/authorized_keys'), 0o600)
        os.chmod(context.full_path('/root/.ssh'), 0o700)
    except:
        api.current_logger().warning('Cannot setup .ssh/authorized_keys')

    lnk = '/etc/systemd/system/multi-user.target.wants/sshd.service'
    try:
        os.symlink('/usr/lib/systemd/system/sshd.service',
            context.full_path(lnk))
    except:
        return False
        api.current_logger().warning('Cannot enable sshd service')

    if get_target_major_version() == '8': # set to LEGACY for 7>8 only
        try:
            with context.open('/etc/crypto-policies/config', 'w+') as f:
                f.write('LEGACY\n')
        except:
            api.current_logger().warning('Cannot set crypto policy to LEGACY')

    return True


# stolen from upgradeinitramfsgenerator.py
def _get_target_kernel_version(context):
    """
    Get the version of the most recent kernel version within the container.
    """
    kernel_version = None

    try:
        results = context.call(['rpm', '-qa', 'kernel-core'], split=True)
        versions = [ver.replace('kernel-core-', '') for ver in results['stdout']]
        api.current_logger().debug(
            'Versions detected {versions}.'
            .format(versions=versions))
        sorted_versions = sorted(versions, key=LooseVersion, reverse=True)
        kernel_version = next(iter(sorted_versions), None)
    except CalledProcessError:
        raise StopActorExecutionError(
            'Cannot get version of the installed kernel.',
            details={'Problem': 'Could not query the currently installed kernel through rmp.'})

    if not kernel_version:
        raise StopActorExecutionError(
            'Cannot get version of the installed kernel.',
            details={'Problem': 'A rpm query for the available kernels did not produce any results.'})

    return kernel_version


def _backup_leapp_dracut_modules(context):
    """
    Move leapp dracut modules that are unneeded for the live initramfs
    """
    try:
        shutil.move(
            context.full_path('/usr/lib/dracut/modules.d/90sys-upgrade'),
            context.full_path('/root'))
        shutil.move(
            context.full_path('/usr/lib/dracut/modules.d/85sys-upgrade-redhat'),
            context.full_path('/root'))
    except:
        api.current_logger().error('Cannot move leapp dracut modules')


def _restore_leapp_dracut_modules(context):
    """
    Restore leapp dracut modules to keep the original state
    """
    try:
        shutil.move(
            context.full_path('/root/90sys-upgrade'),
            context.full_path('/usr/lib/dracut/modules.d'))
        shutil.move(
            context.full_path('/root/85sys-upgrade-redhat'),
            context.full_path('/usr/lib/dracut/modules.d'))
    except:
        # it happens at the very end, ignore
        api.current_logger().warning('Cannot restore leapp dracut modules')


def generate_initramfs(context, boot):
    """
    Generate the initramfs for the live mode
    using dracut modules: dracut-live dracut-squash.
    Silently replace upgrade boot images.
    """
    api.current_logger().info('Building the live initramfs')

    # without this, the [ -w '/boot' ] test failed.
    # found this in the original upgradeinitramfsgenerator actor.
    env = {}
    if get_target_major_version() == '9':
        env = {'SYSTEMD_SECCOMP': '0'}

    _backup_leapp_dracut_modules(context)

    kver = _get_target_kernel_version(context)
    kernel = '/lib/modules/{}/vmlinuz'.format(kver)
    initramfs = boot.initram_path

    cmd = ['dracut', '--verbose', '--compress', 'xz',
           '--add', 'livenet', '--add', 'dmsquash-live',
           '--no-hostonly', '--no-hostonly-default-device',
           '-o', 'plymouth dash resume ifcfg earlykdump',
           '--lvmconf', '--mdadmconf',
           '--kver', kver, '-f', initramfs]

    try:
        context.call(cmd, env=env)
    except:
        raise StopActorExecutionError(
            'Cannot generate the initramfs for the live mode.',
            details={'Problem': 'the dracut command failed: {}'.format(cmd)})

    _restore_leapp_dracut_modules(context)

    if not os.path.isfile(context.full_path(initramfs)):
        initramfs = None
    kernel = '/lib/modules/{}/vmlinuz'.format(kver)
    if not os.path.isfile(context.full_path(kernel)):
        kernel = None
    return (kernel, initramfs)


def fakerootfs():
    FAKEROOTFS_FILE = '/var/lib/leapp/.fakerootfs'
    parameters = []
    with open('/proc/cmdline') as f:
        args = f.read().split(' ')
    for arg in args:
        if arg.startswith('BOOT_IMAGE'):
            continue
        parameters.append(arg.strip())
    try:
        with open(FAKEROOTFS_FILE, 'w+') as f:
            f.write(' '.join(parameters))
    except:
        raise StopActorExecutionError(
            'Cannot prepare the kernel cmdline workaround.',
            details={'Problem': 'cannot write /var/lib/leapp/.fakerootfs'})


def create_etc_issue(context):
    """
    Warn the user regarding the unsupported live mode
    and show instructions
    """
    try:
        msg='\n\n\n' \
            '============================================================\n' \
            '         LEAPP LIVE UPGRADE MODE - *UNSUPPORTED*\n' \
            '============================================================\n' \
            '      DO NOT REBOOT until the upgrade is finished.\n' \
            '      Upgrade logs are sent on tty1 (Ctrl+Alt+F1)\n' \
            '============================================================\n' \
            ' It will automatically reboot unless you touch this file:\n' \
            '   # touch /sysroot/.noreboot\n' \
            '\n' \
            ' If upgrade.autostart=0 is set, run an upgrade manually:\n' \
            '   # upgrade |& tee /sysroot/var/log/leapp/leapp-upgrade.log\n' \
            '\n' \
            ' Log in as root, without password.\n' \
            '\n\n'
        with context.open('/etc/issue', 'w+') as f:
            f.write(msg)
        with context.open('/etc/motd', 'w+') as f:
            f.write(msg)
    except:
        api.current_logger().warning('Cannot write /etc/issue.')
        return False

    return True


def prepare_live_image(userspace, storage, boot, livemode):
    """
    Main function to prepare the live squashfs image
    """
    with mounting.NspawnActions(base_dir=userspace.path) as context:
        service = setup_upgrade_service(context)
        console = setup_console(context)
        sshd = setup_sshd(context, livemode.authorized_keys)
        kernel, initramfs = generate_initramfs(context, boot)
        fstab = configure_fstab(context, storage.fstab)
        mountpoint = create_mountpoint(context)
        root = setup_root_account(context)
        etc_issue = create_etc_issue(context)
        enable_dbus(context)
        setup_nm(context, livemode.nm)

    # Workaround to hide the squashfs root arg in /proc/cmdline
    fakerootfs()

    # To produce the PrepareLiveImageTasks
    return PrepareLiveImageTasks(
        kernel = kernel,
        initramfs = initramfs,
        service = service,
        console = console,
        fstab = fstab,
        mountpoint = mountpoint,
        root = root,
        sshd = sshd,
        etc_issue = etc_issue)
