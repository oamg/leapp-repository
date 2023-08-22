import functools

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.kernel import KernelType


@pytest.mark.parametrize(
    ('rhel_version', 'uname_r', 'expected_kernel_type'),
    (
        ('7.9', '3.10.0-1160.el7.x86_64', KernelType.ORDINARY),
        ('7.9', '3.10.0-1160.rt56.1131.el7.x86_64', KernelType.REALTIME),
        ('8.7', '4.18.0-425.3.1.el8.x86_64', KernelType.ORDINARY),
        ('8.7', '4.18.0-425.3.1.rt7.213.el8.x86_64', KernelType.REALTIME),
        ('9.2', '5.14.0-284.11.1.el9_2.x86_64', KernelType.ORDINARY),
        ('9.2', '5.14.0-284.11.1.rt14.296.el9_2.x86_64', KernelType.REALTIME),
        ('9.3', '5.14.0-354.el9.x86_64', KernelType.ORDINARY),
        ('9.3', '5.14.0-354.el9.x86_64+rt', KernelType.REALTIME),
    )
)
def test_determine_kernel_type_from_uname(rhel_version, uname_r, expected_kernel_type):
    kernel_type = kernel_lib.determine_kernel_type_from_uname(rhel_version, uname_r)
    assert kernel_type == expected_kernel_type


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


@pytest.mark.parametrize('kernel_pkg_with_uname_installed', (True, False))
def test_get_kernel_pkg_info_for_uname_r(monkeypatch, kernel_pkg_with_uname_installed):
    uname_r = '5.14.0-354.el9.x86_64' if kernel_pkg_with_uname_installed else 'other-uname'

    def run_mocked(cmd, *args, **kwargs):
        assert cmd[0:3] == ['rpm', '-q', '--whatprovides']
        output_lines = [
            'kernel-core-5.14.0-354.el9.x86_64.rpm',
            'kernel-rt-core-5.14.0-354.el9.x86_64.rpm',
        ]
        return {'stdout': output_lines}

    def get_uname_provided_by_pkg_mocked(pkg_nevra):
        nevra_uname_table = {
            'kernel-core-5.14.0-354.el9.x86_64.rpm': '5.14.0-354.el9.x86_64',
            'kernel-rt-core-5.14.0-354.el9.x86_64.rpm': '5.14.0-354.el9.x86_64+rt'
        }
        return nevra_uname_table[pkg_nevra]  # Will raise if a different nevra is used than ones from run_mocked

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)
    monkeypatch.setattr(kernel_lib, 'get_uname_r_provided_by_kernel_pkg', get_uname_provided_by_pkg_mocked)

    mk_pkg_info = functools.partial(kernel_lib.KernelPkgInfo, name='', version='', release='', arch='')
    monkeypatch.setattr(kernel_lib,
                        'get_kernel_pkg_info',
                        lambda dummy_nevra: mk_pkg_info(nevra=dummy_nevra))

    if kernel_pkg_with_uname_installed:
        pkg_info = kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)
        assert pkg_info == mk_pkg_info(nevra='kernel-core-5.14.0-354.el9.x86_64.rpm')
    else:
        with pytest.raises(StopActorExecutionError):
            pkg_info = kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)
