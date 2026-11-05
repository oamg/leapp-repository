import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import overlaygen
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FstabEntry, StorageInfo

_SCRATCH_DIR = '/var/lib/leapp/scratch'
_SPACE_NEEDED = 1000
_SCRATCH_RESERVE = 1000

_FORCE_EXT4 = {'LEAPP_OVL_IMG_FS_EXT4': '1'}
_OVL_SIZE = overlaygen._MAGICAL_CONSTANT_OVL_SIZE
_IMAGE_PATH = '/images/root_boot'


class _FreeSpaceMocked:
    """Mock of `_get_fspace` returning the free space configured per path (in MiB)."""

    def __init__(self, free_mib_per_path):
        self.free_mib_per_path = free_mib_per_path
        self.queried_paths = []

    def __call__(self, path, convert_to_mibs=False, coefficient=1.0):
        self.queried_paths.append(path)
        free_mib = int(self.free_mib_per_path[path] * coefficient)
        return free_mib if convert_to_mibs else free_mib * 1024 * 1024


@pytest.mark.parametrize('free_mib', [_SPACE_NEEDED, _SPACE_NEEDED + 1, 5 * _SPACE_NEEDED])
def test_ensure_enough_diskimage_space_passes(monkeypatch, free_mib):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    free_space = _FreeSpaceMocked({_SCRATCH_DIR: free_mib})
    monkeypatch.setattr(overlaygen, '_get_fspace', free_space)

    overlaygen._ensure_enough_diskimage_space(_SPACE_NEEDED, _SCRATCH_DIR)

    assert free_space.queried_paths == [_SCRATCH_DIR]
    assert not api.current_logger().errmsg


@pytest.mark.parametrize('free_mib', [0, _SPACE_NEEDED - 1])
def test_ensure_enough_diskimage_space_error(monkeypatch, free_mib):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(overlaygen, '_get_fspace', _FreeSpaceMocked({_SCRATCH_DIR: free_mib}))

    with pytest.raises(StopActorExecutionError) as err:
        overlaygen._ensure_enough_diskimage_space(_SPACE_NEEDED, _SCRATCH_DIR)

    message = str(err.value)
    assert 'Not enough space available' in message
    assert _SCRATCH_DIR in message
    assert str(_SPACE_NEEDED) in message
    assert api.current_logger().errmsg


@pytest.mark.parametrize('scratch_reserve', [0, 300])
def test_get_mountpoints_free_space_scratch_reserve(monkeypatch, scratch_reserve):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    free_space = _FreeSpaceMocked({'/': 1000, _SCRATCH_DIR: 2000})
    monkeypatch.setattr(overlaygen, '_get_fspace', free_space)

    result = overlaygen._get_mountpoints_free_space(['/', '/var'], _SCRATCH_DIR, scratch_reserve)

    # Non-scratch mountpoints are 5% lower, the scratch one is reduced by the reserve instead
    assert result == {'/': 950, '/var': 2000 - scratch_reserve}
    assert free_space.queried_paths == ['/', _SCRATCH_DIR]


@pytest.mark.parametrize('huge_path, capped_mountpoint', [('/', '/'), (_SCRATCH_DIR, '/var')])
def test_get_mountpoints_free_space_capped(monkeypatch, huge_path, capped_mountpoint):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    free_mib_per_path = {'/': 1000, _SCRATCH_DIR: 2000}
    free_mib_per_path[huge_path] = 2 * overlaygen._MAX_DISK_IMAGE_SIZE_MB
    monkeypatch.setattr(overlaygen, '_get_fspace', _FreeSpaceMocked(free_mib_per_path))

    result = overlaygen._get_mountpoints_free_space(['/', '/var'], _SCRATCH_DIR, 0)

    assert result[capped_mountpoint] == overlaygen._MAX_DISK_IMAGE_SIZE_MB
    assert capped_mountpoint in api.current_logger().infomsg


@pytest.mark.parametrize('src_ver, distro, disk_size, expected', [
    # XFS minimum (130) equals the floor: images are enlarged to the floor and stay XFS
    ('8.10', 'rhel', 0, False),
    ('8.10', 'rhel', 129, False),
    ('8.10', 'ol', 129, False),
    ('9.9', 'rhel', 129, False),
    ('9.9', 'rhel', 130, False),
    # XFS minimum above the floor: images below the XFS minimum use Ext4
    ('9.9', 'ol', 0, True),
    ('9.9', 'ol', 459, True),
    ('9.9', 'ol', 460, False),
    ('10.3', 'rhel', 0, True),
    ('10.3', 'rhel', 299, True),
    ('10.3', 'rhel', 300, False),
    ('10.3', 'ol', 459, True),
    ('10.3', 'ol', 460, False),
])
def test_use_ext4_for_disk_image_per_source(monkeypatch, src_ver, distro, disk_size, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))

    assert overlaygen._use_ext4_for_disk_image(disk_size) is expected


@pytest.mark.parametrize('disk_size', [0, 460, overlaygen._MAX_DISK_IMAGE_SIZE_MB])
@pytest.mark.parametrize('src_ver, distro', [
    ('8.10', 'rhel'),
    ('8.10', 'ol'),
    ('9.9', 'rhel'),
    ('9.9', 'ol'),
    ('10.3', 'rhel'),
    ('10.3', 'ol'),
])
def test_use_ext4_for_disk_image_forced(monkeypatch, src_ver, distro, disk_size):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_ver=src_ver, release_id=distro, envars=_FORCE_EXT4
    ))

    assert overlaygen._use_ext4_for_disk_image(disk_size) is True


# Each disk image is estimated as `_MAGICAL_CONSTANT_OVL_SIZE` + log size of its filesystem
@pytest.mark.parametrize('src_ver, distro, disk_sizes, expected', [
    # XFS log (100) for /, Ext4 log (32) for /boot below the XFS minimum
    ('9.9', 'ol', {'/': 5000, '/boot': 200}, 2 * _OVL_SIZE + 100 + 32),
    # XFS log (64) for /, Ext4 log (32) for /boot below the XFS minimum
    ('10.3', 'rhel', {'/': 5000, '/boot': 200}, 2 * _OVL_SIZE + 64 + 32),
    # XFS log (32) for both, small /boot stays XFS
    ('8.10', 'rhel', {'/': 5000, '/boot': 64}, 2 * _OVL_SIZE + 32 + 32),
    ('9.9', 'ol', {}, 0),
])
def test_estimate_required_space_for_diskimages_per_source(monkeypatch, src_ver, distro, disk_sizes, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))

    assert overlaygen._estimate_required_space_for_diskimages(disk_sizes) == expected


def test_estimate_required_space_for_diskimages_forced(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', release_id='ol', envars=_FORCE_EXT4))

    # Ext4 log (32) for each image, regardless of the size
    expected = 2 * (_OVL_SIZE + 32)
    assert overlaygen._estimate_required_space_for_diskimages({'/': 5000, '/boot': 200}) == expected


def _storage_info(*fstab):
    """Create StorageInfo with fstab entries given as (fs_file, fs_vfstype) pairs."""
    return StorageInfo(fstab=[
        FstabEntry(fs_spec=f'/dev/sda{index}', fs_file=fs_file, fs_vfstype=fs_vfstype, fs_mntops='defaults',
                   fs_freq='0', fs_passno='0')
        for index, (fs_file, fs_vfstype) in enumerate(fstab, start=1)
    ])


@pytest.fixture
def created_images(monkeypatch):
    """Mock the environment of `_prepare_required_mounts` and capture created disk images."""
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    # All fstab mountpoints exist on the system
    monkeypatch.setattr(overlaygen.os.path, 'isdir', lambda path: True)
    monkeypatch.setattr(overlaygen, 'run', lambda cmd: None)
    monkeypatch.setattr(overlaygen, '_create_diskimages_dir', lambda scratch_dir, diskimages_dir: None)

    images = []

    def create_mount_disk_image_mocked(disk_images_directory, path, disk_size):
        images.append((path, disk_size))
        return f'{disk_images_directory}/{path}'

    monkeypatch.setattr(overlaygen, '_create_mount_disk_image', create_mount_disk_image_mocked)
    return images


# Each mountpoint is 5% lower except the one hosting the scratch dir, which is reduced by the reserve.
@pytest.mark.parametrize('src_ver, distro, storage_info, free_mib_per_path, expected_images', [
    pytest.param(
        '9.9', 'ol',
        _storage_info(('/', 'xfs'), ('/boot', 'xfs'), ('/var', 'xfs')),
        {'/': 10000, '/boot': 200, _SCRATCH_DIR: 5000},
        # [(mountpoint, disk size, log size), ...]
        [('/', 9500, 100), ('/boot', 190, 32), ('/var', 5000 - _SCRATCH_RESERVE, 100)],
        id='ol9-small-boot-ext4',
    ),
    pytest.param(
        '9.9', 'rhel',
        _storage_info(('/', 'xfs'), ('/boot', 'xfs'), ('/var', 'xfs')),
        {'/': 10000, '/boot': 200, _SCRATCH_DIR: 5000},
        [('/', 9500, 32), ('/boot', 190, 32), ('/var', 5000 - _SCRATCH_RESERVE, 32)],
        id='rhel9-small-boot-xfs',
    ),
    pytest.param(
        '10.3', 'rhel',
        _storage_info(('/', 'xfs'), ('/boot', 'xfs'), ('/var', 'xfs')),
        {'/': 10000, '/boot': 200, _SCRATCH_DIR: 5000},
        [('/', 9500, 64), ('/boot', 190, 32), ('/var', 5000 - _SCRATCH_RESERVE, 64)],
        id='rhel10-small-boot-ext4',
    ),
    pytest.param(
        '8.10', 'rhel',
        _storage_info(('/', 'xfs')),
        {_SCRATCH_DIR: 5000},
        [('/', 5000 - _SCRATCH_RESERVE, 32)],
        id='el8-root-only',
    ),
    pytest.param(
        '10.3', 'ol',
        _storage_info(('/', 'xfs'), ('/boot/efi', 'vfat'), ('/tmp', 'tmpfs'), ('/home', 'xfs')),
        {'/home': 3000, _SCRATCH_DIR: 5000},
        [('/', 5000 - _SCRATCH_RESERVE, 100), ('/home', 2850, 100)],
        id='ol10-skipped-fs-types',
    ),
])
def test_prepare_required_mounts_creates_images(
        monkeypatch, created_images, src_ver, distro, storage_info, free_mib_per_path, expected_images):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))
    monkeypatch.setattr(overlaygen, '_get_fspace', _FreeSpaceMocked(free_mib_per_path))
    space_checks = []

    def ensure_enough_diskimage_space_mocked(space_needed, directory):
        space_checks.append((space_needed, directory))

    monkeypatch.setattr(overlaygen, '_ensure_enough_diskimage_space', ensure_enough_diskimage_space_mocked)

    result = overlaygen._prepare_required_mounts(_SCRATCH_DIR, '/mounts', storage_info, _SCRATCH_RESERVE)

    assert created_images == [(mountpoint, size) for mountpoint, size, _ in expected_images]
    # Reserve + `_MAGICAL_CONSTANT_OVL_SIZE` and the log of each image
    expected_space = _SCRATCH_RESERVE + sum(_OVL_SIZE + log_size for _, _, log_size in expected_images)
    assert space_checks == [(expected_space, _SCRATCH_DIR)]
    assert sorted(result) == [mountpoint for mountpoint, _, _ in expected_images]
    for mountpoint, loop_mount in result.items():
        assert loop_mount.source == f'{_SCRATCH_DIR}/diskimages/{mountpoint}'
        assert loop_mount.target == overlaygen._mount_dir('/mounts', mountpoint)


def test_prepare_required_mounts_not_enough_space(monkeypatch, created_images):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', release_id='ol'))
    # The scratch partition cannot hold the reserve together with the disk images
    free_space = _FreeSpaceMocked({'/': 10000, _SCRATCH_DIR: _SCRATCH_RESERVE + 100})
    monkeypatch.setattr(overlaygen, '_get_fspace', free_space)
    storage_info = _storage_info(('/', 'xfs'), ('/var', 'xfs'))

    with pytest.raises(StopActorExecutionError):
        overlaygen._prepare_required_mounts(_SCRATCH_DIR, '/mounts', storage_info, _SCRATCH_RESERVE)

    assert not created_images


@pytest.mark.parametrize('envars', [None, _FORCE_EXT4])
@pytest.mark.parametrize('src_ver, distro, expected', [
    ('8.10', 'rhel', 32),
    ('8.10', 'ol', 32),
    ('9.9', 'rhel', 32),
    ('9.9', 'ol', 100),
    ('10.3', 'rhel', 64),
    ('10.3', 'ol', 100),
])
def test_get_fs_log_size_xfs(monkeypatch, src_ver, distro, expected, envars):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro, envars=envars))

    assert overlaygen._get_fs_log_size() == expected


@pytest.mark.parametrize('src_ver, distro', [
    ('8.10', 'rhel'),
    ('8.10', 'ol'),
    ('9.9', 'rhel'),
    ('9.9', 'ol'),
    ('10.3', 'rhel'),
    ('10.3', 'ol'),
])
def test_get_fs_log_size_ext4(monkeypatch, src_ver, distro):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))

    assert overlaygen._get_fs_log_size(ext4=True) == 32


@pytest.mark.parametrize('src_ver, distro, expected', [
    ('8.10', 'rhel', 130),
    ('8.10', 'ol', 130),
    ('9.9', 'rhel', 130),
    ('9.9', 'ol', 460),
    ('10.3', 'rhel', 300),
    ('10.3', 'ol', 460),
])
def test_get_min_xfs_disk_image_size(monkeypatch, src_ver, distro, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))

    assert overlaygen._get_min_xfs_disk_image_size() == expected


def test_format_disk_image_ext4_command(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', release_id='ol'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    commands = []

    def call_with_oserror_handled_mocked(cmd):
        commands.append(cmd)

    monkeypatch.setattr(overlaygen.utils, 'call_with_oserror_handled', call_with_oserror_handled_mocked)

    overlaygen._format_disk_image_ext4(_IMAGE_PATH)

    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[0] == '/sbin/mkfs.ext4'
    assert cmd[cmd.index('-J') + 1] == 'size=32'
    assert cmd[-1] == _IMAGE_PATH


def test_format_disk_image_ext4_error(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', release_id='ol'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def call_with_oserror_handled_mocked(cmd):
        raise CalledProcessError(
            message='Formatting failed.', command=cmd,
            result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': '', 'stderr': 'No space left on device'}
        )

    monkeypatch.setattr(overlaygen.utils, 'call_with_oserror_handled', call_with_oserror_handled_mocked)

    with pytest.raises(StopActorExecutionError) as err:
        overlaygen._format_disk_image_ext4(_IMAGE_PATH)

    assert 'Cannot create Ext4 filesystem' in str(err.value)
    assert _IMAGE_PATH in str(err.value)
    assert api.current_logger().errmsg


@pytest.mark.parametrize('src_ver, distro, expected_log', [
    ('8.10', 'rhel', 32),
    ('8.10', 'ol', 32),
    ('9.9', 'rhel', 32),
    ('9.9', 'ol', 100),
    ('10.3', 'rhel', 64),
    ('10.3', 'ol', 100),
])
def test_format_disk_image_xfs_command(monkeypatch, src_ver, distro, expected_log):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    commands = []

    def call_with_oserror_handled_mocked(cmd):
        commands.append(cmd)

    monkeypatch.setattr(overlaygen.utils, 'call_with_oserror_handled', call_with_oserror_handled_mocked)

    overlaygen._format_disk_image_xfs(_IMAGE_PATH)

    assert len(commands) == 1
    cmd = commands[0]
    assert cmd[0] == '/sbin/mkfs.xfs'
    assert cmd[cmd.index('-l') + 1] == f'size={expected_log}m'
    assert cmd[-1] == _IMAGE_PATH


def test_format_disk_image_xfs_error(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='9.9', release_id='ol'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    def call_with_oserror_handled_mocked(cmd):
        raise CalledProcessError(
            message='Formatting failed.', command=cmd,
            result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': '', 'stderr': 'No space left on device'}
        )

    # OSError is turned into StopActorExecutionError by `utils.call_with_oserror_handled` itself
    monkeypatch.setattr(overlaygen.utils, 'call_with_oserror_handled', call_with_oserror_handled_mocked)

    with pytest.raises(StopActorExecutionError) as err:
        overlaygen._format_disk_image_xfs(_IMAGE_PATH)

    assert 'Cannot create XFS filesystem' in str(err.value)
    assert _IMAGE_PATH in str(err.value)
    assert api.current_logger().errmsg


@pytest.fixture
def disk_image_calls(monkeypatch):
    """Capture `dd` commands and formatting calls of `_create_mount_disk_image` instead of running them."""
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    calls = {'dd': [], 'formatted': []}

    def call_with_failure_hint_mocked(cmd, hint):
        calls['dd'].append(cmd)

    monkeypatch.setattr(overlaygen.utils, 'call_with_failure_hint', call_with_failure_hint_mocked)
    monkeypatch.setattr(overlaygen, '_format_disk_image_ext4', lambda path: calls['formatted'].append(('ext4', path)))
    monkeypatch.setattr(overlaygen, '_format_disk_image_xfs', lambda path: calls['formatted'].append(('xfs', path)))
    return calls


@pytest.mark.parametrize('src_ver, distro, disk_size, expected_seek, expected_fs', [
    # XFS minimum (130) equals the floor: small images are enlarged and stay XFS
    ('8.10', 'rhel', 64, 130, 'xfs'),
    ('8.10', 'ol', 129, 130, 'xfs'),
    ('9.9', 'rhel', 129, 130, 'xfs'),
    ('9.9', 'rhel', 130, 130, 'xfs'),
    # XFS minimum above the floor: Ext4 below the XFS minimum, enlarged only below the floor
    ('9.9', 'ol', 64, 130, 'ext4'),
    ('9.9', 'ol', 459, 459, 'ext4'),
    ('9.9', 'ol', 460, 460, 'xfs'),
    ('10.3', 'rhel', 299, 299, 'ext4'),
    ('10.3', 'rhel', 300, 300, 'xfs'),
    ('10.3', 'ol', 459, 459, 'ext4'),
    ('10.3', 'ol', 460, 460, 'xfs'),
])
def test_create_mount_disk_image_per_source(
        monkeypatch, disk_image_calls, src_ver, distro, disk_size, expected_seek, expected_fs):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver=src_ver, release_id=distro))

    image_path = overlaygen._create_mount_disk_image('/images', '/boot', disk_size)

    assert image_path == _IMAGE_PATH
    assert len(disk_image_calls['dd']) == 1
    assert f'seek={expected_seek}' in disk_image_calls['dd'][0]
    assert disk_image_calls['formatted'] == [(expected_fs, _IMAGE_PATH)]
    # Enlarging the image is reported
    assert bool(api.current_logger().warnmsg) == (expected_seek > disk_size)


@pytest.mark.parametrize('src_ver, distro', [
    ('8.10', 'rhel'),
    ('8.10', 'ol'),
    ('9.9', 'rhel'),
    ('9.9', 'ol'),
    ('10.3', 'rhel'),
    ('10.3', 'ol'),
])
def test_create_mount_disk_image_forced_ext4(monkeypatch, disk_image_calls, src_ver, distro):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        src_ver=src_ver, release_id=distro, envars=_FORCE_EXT4
    ))

    overlaygen._create_mount_disk_image('/images', '/boot', 1024)

    assert disk_image_calls['formatted'] == [('ext4', _IMAGE_PATH)]
