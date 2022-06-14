import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import checkfstabxfsoptions
from leapp.models import FstabEntry, StorageInfo
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


def _myint_gen():
    i = 0
    while True:
        yield i
        i += 1


def _gen_fs_ent(fstype='ext4', mntops='auto', val=_myint_gen()):
    return FstabEntry(
        fs_spec='/path/spec/{}'.format(next(val)),
        fs_file='/path/file/{}'.format(next(val)),
        fs_vfstype=fstype,
        fs_mntops=mntops,
        fs_freq='1',
        fs_passno='1',
    )


@pytest.mark.parametrize('fstab', [
    [_gen_fs_ent()],
    [_gen_fs_ent() for dummy in range(4)],
    [_gen_fs_ent(), _gen_fs_ent('ext4', 'auto,quota,huge_file')],
    # checking that problematic options are ignored for non-xfs FS
    [_gen_fs_ent(), _gen_fs_ent('ext4', 'auto,barier,huge_file')],
    [_gen_fs_ent('ext4', i) for i in checkfstabxfsoptions.REMOVED_XFS_OPTIONS],
    [_gen_fs_ent(i, 'nobarrier') for i in ('ext4', 'ext3', 'vfat', 'btrfs')],
])
def test_no_xfs_option(fstab, current_actor_context):
    current_actor_context.feed(StorageInfo(fstab=fstab))
    current_actor_context.run()
    report = current_actor_context.consume(Report)
    assert not report


# each item == one fstab
problematic_fstabs = [[_gen_fs_ent('xfs', ','.join(checkfstabxfsoptions.REMOVED_XFS_OPTIONS))]]
for opt in checkfstabxfsoptions.REMOVED_XFS_OPTIONS:
    problematic_fstabs.append([_gen_fs_ent('xfs', opt)])
    problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', opt)])
    problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', opt), _gen_fs_ent()])
    pre_opts = '{},auto,quota'.format(opt)
    in_opts = 'auto,{},quota'.format(opt)
    post_opts = 'auto,quota,{}'.format(opt)
    problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', pre_opts)])
    problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', in_opts)])
    problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', post_opts)])
# ensure we catch even cases when a value is expected to be specified; we know just this
# one case, so it should be representative it's working like that..
problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', 'defaults,ihashsize=4096')])
problematic_fstabs.append([_gen_fs_ent(), _gen_fs_ent('xfs', 'defaults,ihashsize=4096,auto')])


@pytest.mark.parametrize('fstab', problematic_fstabs)
def test_removed_xfs_option(fstab, current_actor_context):
    current_actor_context.feed(StorageInfo(fstab=fstab))
    current_actor_context.run()
    report = current_actor_context.consume(Report)
    assert report and len(report) == 1
    assert is_inhibitor(report[0].report)
