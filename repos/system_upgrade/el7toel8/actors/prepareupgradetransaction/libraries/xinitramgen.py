import os
from itertools import chain

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import preparetransaction
from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.models import BootContent

_REQUIRED_PACKAGES = [
    'biosdevname',
    'binutils',
    'cifs-utils',
    'device-mapper-multipath',
    'dracut',
    'dracut-config-generic',
    'dracut-config-rescue',
    'dracut-network',
    'dracut-tools',
    'fcoe-utils',
    'hostname',
    'iscsi-initiator-utils',
    'kbd',
    'kernel',
    'kernel-core',
    'kernel-modules',
    'keyutils',
    'lldpad',
    'lvm2',
    'mdadm',
    'nfs-utils',
    'openssh-clients',
    'plymouth',
    'rpcbind',
    'systemd-container',
    'tar',
]


def prepare_el8_userspace(overlayfs, userspace_dir, enabled_repos):
    overlay_target = os.path.join(overlayfs.merged, 'el8target')
    run(['rm', '-rf', userspace_dir])
    run(['mkdir', '-p', userspace_dir])
    run(['mkdir', '-p', overlay_target])
    try:
        run(['mount', '--bind', userspace_dir, overlay_target])
        repos_opt = [['--enablerepo', repo] for repo in enabled_repos]
        repos_opt = list(chain(*repos_opt))
        preparetransaction.guard_container_call(
            overlayfs_info=overlayfs,
            cmd=[
                'dnf',
                'install',
                '-y',
                '--nogpgcheck',
                '--setopt=module_platform_id=platform:el8',
                '--releasever', '8',
                '--installroot', '/el8target',
                '--disablerepo', '*'
            ] + repos_opt + _REQUIRED_PACKAGES,
            print_output=True
        )
    finally:
        run(['umount', '-fl', overlay_target])
    run(['mkdir', '-p', os.path.join(userspace_dir, 'artifacts')])


def copy_modules(userspace_dir):
    sysuprh_path = api.get_actor_folder_path('dracut/85sys-upgrade-redhat')
    sysup_path = api.get_actor_folder_path('dracut/90sys-upgrade')
    if not sysup_path or not sysuprh_path:
        raise StopActorExecutionError(
            message='Could not find required dracut modules to generate '
                    'initram disk'
        )
    run([
        'cp', '-a',
        api.get_actor_folder_path('dracut'),
        userspace_dir
    ])


def generate_initram_disk(userspace_dir):
    # Copy dracut modules to el8 userspace
    copy_modules(userspace_dir)
    # Copy generate-initram.sh
    run([
        'cp',
        '-a',
        api.get_actor_file_path('generate-initram.sh'),
        userspace_dir
    ])
    run([
        'systemd-nspawn',
        '--register=no',
        '--quiet',
        '-D', userspace_dir,
        '/bin/sh', '/generate-initram.sh'
    ])

def remove_userspace(userspace_dir):
    try:
        run(['rm', '-rf', userspace_dir])
    except Exception:
        api.current_logger().info('Removal of el8 userspace failed - Failure ignored', exc_info=True)

def copy_boot_files(userspace_dir):
    kernel = 'vmlinuz-upgrade.x86_64'
    initram = 'initramfs-upgrade.x86_64.img'
    content = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        initram_path=os.path.join('/boot', initram)
    )

    run(['cp', '-a', os.path.join(userspace_dir, 'artifacts', kernel), content.kernel_path])
    run(['cp', '-a', os.path.join(userspace_dir, 'artifacts', initram), content.initram_path])

    api.produce(content)
