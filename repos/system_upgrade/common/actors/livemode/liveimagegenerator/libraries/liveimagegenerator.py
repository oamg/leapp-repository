import os
import os.path
import shutil
import subprocess
from distutils.version import LooseVersion

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError, run

LEAPP_LIVE_IMAGE = '/var/lib/leapp/live-upgrade.img'
LEAPP_LIVEOS_DIR = '/var/lib/leapp/tmp'
DEFAULT_XFS_SIZE = 3072 # MB


def _shell(command):
    p = subprocess.Popen(command,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,
                     close_fds=True,
                     shell=True,
                     universal_newlines=True)
    p.wait()
    output = []
    while True:
        line = p.stdout.readline().rstrip('\n')
        if line:
            output.append(line)
        else:
            break
    return (p.returncode, output)


def setup_boot_content(context, tasks, boot):
    """
    Silently replace upgrade boot images.
    """
    api.current_logger().info('Setup the live boot content')

    if not tasks.kernel or not tasks.initramfs:
        raise StopActorExecutionError(
            'Cannot install the boot images for the live mode.',
            details={'Problem': 'kernel: %s, initramfs: %s.'
            % (tasks.kernel, tasks.initramfs)})

    try:
        os.unlink(boot.kernel_path)
        os.unlink(boot.initram_path)
    except:
        pass

    try:
        context.copy_from(tasks.kernel, boot.kernel_path)
        context.copy_from(tasks.initramfs, boot.initram_path)
    except:
        raise StopActorExecutionError(
            'Cannot install the boot images for the live mode.',
            details={'Problem': 'copy to host failed.'})

    if not os.path.isfile(boot.initram_path):
        return (None, None)
    return (boot.kernel_path, boot.initram_path)


def _backup_dnf_cache(context):
    """
    Move temporary the DNF cache outside the target userspace
    """
    try:
        shutil.move(context.full_path('/var/cache/dnf'), '/var/lib/leapp')
        context.makedirs('/var/cache/dnf')
    except:
        api.current_logger().warning('Cannot backup the DNF cache.')


def _restore_dnf_cache(context):
    """
    Restore the DNF cache inside the target userspace
    """
    try:
        if os.path.isdir(context.full_path('/var/cache/dnf')):
            context.call(['rm', '-rf', '/var/cache/dnf'])
        shutil.move('/var/lib/leapp/dnf', context.full_path('/var/cache'))
    except:
        api.current_logger().warning('Cannot restore the DNF cache.')


def _create_liveos_xfs(liveos_dir):
    """
    Create XFS image into LiveOS/rootfs.img
    """
    xfs_size = os.getenv('LEAPP_LIVE_XFS_SIZE', DEFAULT_XFS_SIZE)
    try:
        run(['rm', '-rf', liveos_dir])
        os.makedirs("{}/LiveOS".format(liveos_dir))
        run(['mkfs.xfs', '-d', 'file,name=%s/LiveOS/rootfs.img,size=%sm'
            % (liveos_dir, xfs_size)])
    except CalledProcessError as e:
        raise StopActorExecutionError(
           'Cannot mkfs temporary LiveOS image.',
           details={'details': 'the mkfs command failed.'}
        )


def _unmount_tmp_liveos(liveos_dir):
    try:
        run(['umount', '-fl', '{}_mnt'.format(liveos_dir)])
    except:
        pass


def _copy_rootfs(userspace_dir, liveos_dir):
    """
    Copy the target userspace content into the XFS image
    """
    try:
        run(['rm', '-rf', '{}_mnt'.format(liveos_dir)])
        os.makedirs('{}_mnt'.format(liveos_dir))
        run(['mount', '{}/LiveOS/rootfs.img'.format(liveos_dir),
             '{}_mnt'.format(liveos_dir)])
    except CalledProcessError:
        _unmount_tmp_liveos(liveos_dir)
        raise StopActorExecutionError(
           'Cannot mount temporary LiveOS image.',
           details={'details': 'none'}
        )

    try:
        # NOTE: this safe approach requires twice the target userspace size.
        # To avoid this, it would need an actor that creates this image
        # before the target userspace & mount it in /var/lib/leapp/elXuserspace
        # but it could cause issues with other actors that remove this directory
        # When mounted, its removal would lead to an EBUSY errno.
        api.current_logger().info('Copying the target userspace to the LiveOS')
        ret, out = _shell('/bin/cp -fapZ %s/* %s_mnt'
                        % (userspace_dir, liveos_dir))
        if ret != 0:
            api.current_logger().error(
                'Cannot the target userspace to the LiveOS'
            )
    except:
        _unmount_tmp_liveos(liveos_dir)
        raise StopActorExecutionError(
           'Cannot the target userspace to the LiveOS',
           details={'details': 'none'}
        )

    _unmount_tmp_liveos(liveos_dir)


def lighten_target_userpace(context):
    """
    Remove unneeded files from the target userspace
    """
    try:
        ret, out = _shell('rm -rf {}/artifacts'.format(context.base_dir))
        ret, out = _shell('rm -rf {}/boot/*'.format(context.base_dir))
    except:
        api.current_logger().warning(
           'Cannot remove /boot content from the live image.'
        )


def build_squashfs(context, livemode):
    """
    Generate the live rootfs image based on the target userspace
    """
    api.current_logger().info('Building the squashfs image')

    liveos_dir = livemode.temp_dir or LEAPP_LIVEOS_DIR
    squashfs_filename = livemode.squashfs or LEAPP_LIVE_IMAGE

    if not livemode.with_cache:
        _backup_dnf_cache(context)

    _create_liveos_xfs(liveos_dir)
    _copy_rootfs(context.base_dir, liveos_dir)

    cwd = os.getcwd()
    os.chdir(liveos_dir)
    try:
        os.unlink(squashfs_filename)
    except:
        pass
    try:
        run(['mksquashfs', '.', squashfs_filename])
    except CalledProcessError:
        if not livemode.with_cache:
            _restore_dnf_cache(context)
        raise StopActorExecutionError(
           'Cannot pack the target userspace into a squash image. ',
           details={'details': 'a problem occurs with mksquashfs.'}
        )
    os.chdir(cwd)

    try:
        run(['rm', '-rf', liveos_dir])
        os.rmdir('{}_mnt'.format(liveos_dir))
    except:
        api.current_logger().warning('Cannot remove temporary LiveOS dir')

    if not livemode.with_cache:
        _restore_dnf_cache(context)

    if not os.path.isfile(squashfs_filename):
        return None
    return squashfs_filename


def generate_live_image(livemode, userspace, tasks, boot):
    """
    Main function to generate the live mode artifacts:
     - vmlinuz-upgrade.x86_64
     - initramfs-upgrade.x86_64.img
     - leapp-live-upgrade.img
    Update the upgrade boot entry with specific parameters afterwards.
    """

    with mounting.NspawnActions(base_dir=userspace.path) as context:
        kernel, initramfs = setup_boot_content(context, tasks, boot)
        lighten_target_userpace(context)
        squashfs = build_squashfs(context, livemode)

    return (kernel, initramfs, squashfs)
