from collections import namedtuple

from leapp.libraries.common import overlaygen


class RunMocked(object):
    def __init__(self):
        self.invocations = []

    def __call__(self, *args, **kwargs):
        self.invocations.append((args, kwargs))


def test_prepare_required_mounts_image_size_capping(monkeypatch):
    """ Test whether having a very large disk will not create very large image. """
    MountPoint = namedtuple('MountPoint', 'fs_file')
    mount_points = [MountPoint(fs_file='/big_disk')]
    monkeypatch.setattr(overlaygen, '_get_mountpoints', lambda storage_info: mount_points)
    monkeypatch.setattr(overlaygen, '_get_scratch_mountpoint', lambda *args: '/scratch')
    monkeypatch.setattr(overlaygen, '_create_diskimages_dir', lambda *args: None)
    monkeypatch.setattr(overlaygen, '_ensure_enough_diskimage_space', lambda *args: None)

    mountpoint_sizes = {
        '/big_disk': 20*(1024**2),  # 20TB
        '/scratch': 20  # Arbitrary, irrelevant for this test
    }
    monkeypatch.setattr(overlaygen, '_get_fspace', lambda mount, *args, **kwargs: mountpoint_sizes[mount])
    monkeypatch.setattr(overlaygen, 'run', RunMocked())

    def create_disk_image_mock(disk_images_dir, mountpoint, disk_size):
        assert mountpoint == '/big_disk'
        assert disk_size == overlaygen._MAX_DISK_IMAGE_SIZE_MB

    monkeypatch.setattr(overlaygen, '_create_mount_disk_image', create_disk_image_mock)

    storage_info = None  # Should not be used in the code due to how we mocked overlaygen functions
    overlaygen._prepare_required_mounts('/scratch', '/mounts', storage_info, 100)
