import pytest

from leapp.libraries.common.fstab import drop_xfs_options


DUMMY_FSTAB = [
    '',
    '# These could be the contents of /etc/fstab.',
    '# Next line is a comment and should not be modified.',
    '#/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-root /           xfs     defaults,nobarrier        0 0',
    '#',
    '# Make sure the braces on second to last line are replaced with a filesystem and some mount options.',
    '',
    '/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-root /           xfs     defaults        0 0',
    'UUID=7d8635ff-fb7c-4e9f-a1ef-13ad8de15b9b /boot       {}     {}        0 0',
    '/dev/mapper/rhel_ibm--p8--kvm--03--guest--02-swap swap        swap    defaults        0 0',
]


@pytest.mark.parametrize('filesystem,options', [
    ('xfs', 'defaults'),
    ('xfs', 'ro,rw'),
    ('xfs', 'rsize=32768,wsize=8192,bg,noauto,x-systemd.automount,noatime,nosuid,nodev,intr,nfsvers=3'),
    ('ext4', 'defaults'),
    ('nfs', 'defaults'),
    ('nfs', 'defaults,nobarrier'),
    ('nfs', 'delaylog,irixsgid,osynciso,barrier,defaults,nodelaylog,ihashsize,osyncisdsync,nobarrier'),
])
def test_no_xfs_options(filesystem, options):
    lines = DUMMY_FSTAB[:]
    lines[-2].format(filesystem, options)
    # check that no line has changed
    assert lines == drop_xfs_options(lines)


@pytest.mark.parametrize('filesystem,options,options_expected', [
    ('xfs', 'defaults,nobarrier', 'defaults'),
    ('xfs', 'nobarrier,defaults', 'defaults'),
    ('xfs', 'delaylog,irixsgid,osyncisosync,barrier,ro,nodelaylog,ihashsize,osyncisdsync,nobarrier', 'ro'),
])
def test_xfs_options(filesystem, options, options_expected):
    lines = DUMMY_FSTAB[:]
    expected = DUMMY_FSTAB[:]
    lines[-2].format(filesystem, options)
    expected[-2].format(filesystem, options_expected)
    assert expected == drop_xfs_options(lines)
