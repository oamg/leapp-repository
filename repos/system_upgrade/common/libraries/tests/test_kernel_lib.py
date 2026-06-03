import functools

import pytest

from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.kernel import KernelPageSize, KernelType
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api


@pytest.mark.parametrize(
    ('version', 'uname_r', 'expected_kernel_type'),
    (
        # (version, virtual_version)
        (('7.9', None), '3.10.0-1160.el7.x86_64', KernelType.ORDINARY),
        (('7.9', None), '3.10.0-1160.rt56.1131.el7.x86_64', KernelType.REALTIME),
        (('8.7', None), '4.18.0-425.3.1.el8.x86_64', KernelType.ORDINARY),
        (('8.7', None), '4.18.0-425.3.1.rt7.213.el8.x86_64', KernelType.REALTIME),
        (('9.2', None), '5.14.0-284.11.1.el9_2.x86_64', KernelType.ORDINARY),
        (('9.2', None), '5.14.0-284.11.1.rt14.296.el9_2.x86_64', KernelType.REALTIME),
        (('9.3', None), '5.14.0-354.el9.x86_64', KernelType.ORDINARY),
        (('9.3', None), '5.14.0-354.el9.x86_64+rt', KernelType.REALTIME),
        (('9.3', None), '5.14.0-354.el9.aarch64+64k', KernelType.ORDINARY),
        (('9.3', None), '5.14.0-354.el9.aarch64+rt-64k', KernelType.REALTIME),
        (('9.3', None), '5.14.0-354.el9.aarch64+rt_64k', KernelType.REALTIME),
        # centos
        (('8', '8.7'), '4.18.0-425.3.1.el8.x86_64', KernelType.ORDINARY),
        (('8', '8.7'), '4.18.0-425.3.1.rt7.213.el8.x86_64', KernelType.REALTIME),
        (('9', '9.2'), '5.14.0-284.11.1.el9_2.x86_64', KernelType.ORDINARY),
        (('9', '9.2'), '5.14.0-284.11.1.rt14.296.el9_2.x86_64', KernelType.REALTIME),
        (('9', '9.3'), '5.14.0-354.el9.x86_64', KernelType.ORDINARY),
        (('9', '9.3'), '5.14.0-354.el9.x86_64+rt', KernelType.REALTIME),
        (('9', '9.3'), '5.14.0-354.el9.aarch64+64k', KernelType.ORDINARY),
        (('9', '9.3'), '5.14.0-354.el9.aarch64+rt-64k', KernelType.REALTIME),
        (('9', '9.3'), '5.14.0-354.el9.aarch64+rt_64k', KernelType.REALTIME),
    )
)
def test_determine_kernel_type_from_uname(monkeypatch, version, uname_r, expected_kernel_type):
    real_ver, virtual_ver = version
    # needed to for lookups of virtual versions in matches_version
    actor_mock = CurrentActorMocked(
        release_id='centos' if '.' not in real_ver else 'rhel',
        src_ver=real_ver,
        dst_ver='irrelevant',
        virtual_source_version=virtual_ver or real_ver,
        virtual_target_version='irrelevant',
    )
    monkeypatch.setattr(api, 'current_actor', actor_mock)

    kernel_type = kernel_lib.determine_kernel_type_from_uname(real_ver, uname_r)
    assert kernel_type == expected_kernel_type


@pytest.mark.parametrize(
    ('uname_r', 'expected_page_size'),
    (
        ('5.14.0-354.el9.x86_64', KernelPageSize.DEFAULT),
        ('5.14.0-354.el9.x86_64+rt', KernelPageSize.DEFAULT),
        ('4.18.0-425.3.1.rt7.213.el8.x86_64', KernelPageSize.DEFAULT),
        ('5.14.0-354.el9.aarch64+64k', KernelPageSize.LARGE),
        ('5.14.0-354.el9.aarch64+rt-64k', KernelPageSize.LARGE),
        ('5.14.0-354.el9.aarch64+rt_64k', KernelPageSize.LARGE),
    )
)
def test_determine_kernel_page_size_from_uname(uname_r, expected_page_size):
    page_size = kernel_lib.determine_kernel_page_size_from_uname(uname_r)
    assert page_size == expected_page_size


def test_get_uname_r_provided_by_kernel_pkg(monkeypatch):
    kernel_nevra = 'kernel-core-5.14.0-354.el9.x86_64'

    def run_mocked(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-q', '--provides', kernel_nevra]
        output_lines = [
            'kmod(virtio_ring.ko)',
            'kernel(zlib_inflate_blob) = 0x65408378',
            'kernel-uname-r = 5.14.0-354.el9.x86_64'
        ]
        return {'stdout': output_lines}

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)

    uname_r = kernel_lib.get_uname_r_provided_by_kernel_pkg(kernel_nevra)
    assert uname_r == '5.14.0-354.el9.x86_64'


@pytest.mark.parametrize(
    ('uname_r', 'expected_nevra'),
    (
        ('5.14.0-354.el9.x86_64', 'kernel-core-5.14.0-354.el9.x86_64.rpm'),
        ('5.14.0-354.el9.x86_64+rt', 'kernel-rt-core-5.14.0-354.el9.x86_64.rpm'),
        ('5.14.0-687.el9.aarch64+64k', 'kernel-64k-core-5.14.0-687.el9.aarch64.rpm'),
        # RPM provides +rt_64k (underscore), uname -r reports +rt-64k (hyphen)
        ('5.14.0-687.el9.aarch64+rt-64k', 'kernel-rt-64k-core-5.14.0-687.el9.aarch64.rpm'),
        # Reversed: uname -r reports +rt_64k (underscore)
        ('5.14.0-687.el9.aarch64+rt_64k', 'kernel-rt-64k-core-5.14.0-687.el9.aarch64.rpm'),
        ('unknown', None),
    )
)
def test_get_kernel_pkg_info_for_uname_r(monkeypatch, uname_r, expected_nevra):
    def run_mocked(cmd, *args, **kwargs):
        assert cmd[0:3] == ['rpm', '-q', '--whatprovides']
        output_lines = [
            'kernel-core-5.14.0-354.el9.x86_64.rpm',
            'kernel-rt-core-5.14.0-354.el9.x86_64.rpm',
            'kernel-64k-core-5.14.0-687.el9.aarch64.rpm',
            'kernel-rt-64k-core-5.14.0-687.el9.aarch64.rpm',
        ]
        return {'stdout': output_lines}

    def get_uname_provided_by_pkg_mocked(pkg_nevra):
        nevra_uname_table = {
            'kernel-core-5.14.0-354.el9.x86_64.rpm': '5.14.0-354.el9.x86_64',
            'kernel-rt-core-5.14.0-354.el9.x86_64.rpm': '5.14.0-354.el9.x86_64+rt',
            'kernel-64k-core-5.14.0-687.el9.aarch64.rpm': '5.14.0-687.el9.aarch64+64k',
            'kernel-rt-64k-core-5.14.0-687.el9.aarch64.rpm': '5.14.0-687.el9.aarch64+rt_64k',
        }
        return nevra_uname_table[pkg_nevra]

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)
    monkeypatch.setattr(kernel_lib, 'get_uname_r_provided_by_kernel_pkg', get_uname_provided_by_pkg_mocked)

    mk_pkg_info = functools.partial(kernel_lib.KernelPkgInfo, name='', version='', release='', arch='')
    monkeypatch.setattr(kernel_lib,
                        'get_kernel_pkg_info',
                        lambda dummy_nevra: mk_pkg_info(nevra=dummy_nevra))

    if expected_nevra:
        pkg_info = kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)
        assert pkg_info == mk_pkg_info(nevra=expected_nevra)
    else:
        with pytest.raises(kernel_lib.KernelPackageInfoError):
            kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)
