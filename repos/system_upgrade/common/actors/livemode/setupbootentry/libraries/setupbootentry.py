import os
import os.path

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run


def _get_rdlvm_args():
    # should we not check args returned by grubby instead?
    with open('/proc/cmdline') as f:
        cmdline = f.read().strip().split(' ')
    return [arg for arg in cmdline if arg.startswith('rd.lvm')]


def _get_device_uuid(mnt):
    """
    Find the mount point where resides the squashfs image
    and return the corresponding device UUID.
    """
    while not os.path.ismount(mnt):
        mnt = os.path.dirname(mnt)

    mounts = []
    with open('/proc/mounts') as f:
        mounts = f.readlines()

    devname = ''
    for mount in mounts:
        args = mount.strip().split(' ')
        if args[1] != mnt:
            continue
        devname = args[0]

    uuid = ''
    dm = os.path.basename(os.readlink(devname))
    for uuid in os.listdir('/dev/disk/by-uuid'):
        path = '/dev/disk/by-uuid/{}'.format(uuid)
        if os.path.basename(os.readlink(path)) == dm:
            break

    return uuid


def prepare_live_cmdline(squashfs, livemode):
    """
    Prepare cmdline parameters for the live mode
    """
    # boot locally by default
    liveimg = os.path.basename(squashfs)
    livedir = os.path.dirname(squashfs)
    root = 'root=live:UUID={}'.format(_get_device_uuid(livedir))
    livedir_arg = 'rd.live.dir={}'.format(livedir)
    liveimg_arg = 'rd.live.squashimg={}'.format(liveimg)

    # if an URL is defined, boot over the network (http, nfs, ftp, ...)
    if livemode.url:
        root = 'root=live:{}'.format(livemode.url)
        livedir_arg = ''
        liveimg_arg = ''

    api.current_logger().info(
        'the live mode image will boot with:\n%s'
        % ' '.join([root, livedir_arg, liveimg_arg])
    )

    # set optional parameters
    ip_arg = livemode.dracut_network or ''
    if ip_arg:
        ip_arg += ' rd.neednet=1'
    debug = 'debug' if os.getenv('LEAPP_DEVEL_DEBUG', '0') == '1' else ''
    autostart = 'upgrade.autostart=0' if not livemode.autostart else ''
    strace = 'upgrade.strace=%s' % livemode.strace if livemode.strace else ''

    return (root, {
        'livedir': livedir_arg,
        'liveimg': liveimg_arg,
        'ip': ip_arg,
        'debug': debug,
        'autostart': autostart,
        'strace': strace
    })


def setup_boot_entry(root, args, boot):
    """
    Use grubby to setup live boot images
    """
    # remove any existing entry for the upgrade kernel
    cmd = ['/usr/sbin/grubby', '--remove-kernel', boot.kernel_path]
    try:
        run(cmd)
    except CalledProcessError:
        api.current_logger().warning(
            'Could not remove {} entry. May be ignored '
            'if the entry did not exist.'.format(boot.kernel_path)
        )

    # setup again the upgrade grub entry
    to_set = ' '.join(args.values())
    to_set += ' rw enforcing=0 rd.plymouth=0 plymouth.enable=0'
    cmd = ['/usr/sbin/grubby',
           '--add-kernel', boot.kernel_path,
           '--initrd', boot.initram_path,
           '--title', 'RHEL-Live-Upgrade',
           '--copy-default',
           '--make-default',
           '--args', to_set]
    # and configure the root parameter
    setroot = ['/usr/sbin/grubby',
               '--update-kernel', boot.kernel_path,
               '--args', root]
    try:
        run(cmd)
        run(setroot)
    except CalledProcessError:
        raise StopActorExecutionError(
           'Cannot configure bootloader for live mode.',
           details={'details': 'the grubby command failed: {}'.format(cmd)}
        )

    # live mode fails with ro and rd.lvm* args so remove them
    to_remove = _get_rdlvm_args() + ['ro', 'rhgb', 'quiet']
    cmd = ['/usr/sbin/grubby',
           '--update-kernel', boot.kernel_path,
           '--remove-args', ' '.join(to_remove)]
    try:
        run(cmd)
    except CalledProcessError:
        raise StopActorExecutionError(
           'Cannot remove some args for live mode.',
           details={'details': 'the grubby command failed: {}'.format(cmd)}
        )

    return True
