import pytest

from leapp.libraries.common import kernel as kernel_lib
from leapp.libraries.common.kernel import KernelPageSize, KernelType
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError


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
        # centos
        (('8', '8.7'), '4.18.0-425.3.1.el8.x86_64', KernelType.ORDINARY),
        (('8', '8.7'), '4.18.0-425.3.1.rt7.213.el8.x86_64', KernelType.REALTIME),
        (('9', '9.2'), '5.14.0-284.11.1.el9_2.x86_64', KernelType.ORDINARY),
        (('9', '9.2'), '5.14.0-284.11.1.rt14.296.el9_2.x86_64', KernelType.REALTIME),
        (('9', '9.3'), '5.14.0-354.el9.x86_64', KernelType.ORDINARY),
        (('9', '9.3'), '5.14.0-354.el9.x86_64+rt', KernelType.REALTIME),
        (('9', '9.3'), '5.14.0-354.el9.aarch64+64k', KernelType.ORDINARY),
        (('9', '9.3'), '5.14.0-354.el9.aarch64+rt-64k', KernelType.REALTIME),
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
    ('getconf_output', 'expected_page_size'),
    (
        ('4096', KernelPageSize.PAGE_SIZE_4K),
        ('65536', KernelPageSize.PAGE_SIZE_64K),
    )
)
def test_determine_kernel_page_size(monkeypatch, getconf_output, expected_page_size):
    def run_mocked(cmd, *args, **kwargs):
        assert cmd == ['getconf', 'PAGE_SIZE']
        return {'stdout': getconf_output}

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)
    page_size = kernel_lib.determine_kernel_page_size()
    assert page_size == expected_page_size


def test_determine_kernel_page_size_getconf_failure(monkeypatch):
    def run_mocked(cmd, *args, **kwargs):
        raise CalledProcessError(message='Command getconf PAGE_SIZE failed with exit code 1.', command=cmd,
                                 result={'exit_code': 1, 'stdout': '', 'stderr': ''})

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    page_size = kernel_lib.determine_kernel_page_size()
    assert page_size == KernelPageSize.PAGE_SIZE_4K
    assert api.current_logger.warnmsg


def _mock_context_for_file_list(kernel_nevra, file_lines):
    class _MockContext:
        def call(self, cmd, *args, **kwargs):  # pylint: disable=no-self-use
            assert cmd == ['rpm', '-q', '-l', kernel_nevra]
            return {'stdout': file_lines}
    return _MockContext()


def test_get_uname_r_provided_by_kernel_pkg():
    kernel_nevra = 'kernel-core-5.14.0-354.el9.x86_64'
    file_lines = [
        '/lib/modules',
        '/lib/modules/5.14.0-354.el9.x86_64',
        '/lib/modules/5.14.0-354.el9.x86_64/.vmlinuz.hmac',
        '/lib/modules/5.14.0-354.el9.x86_64/vmlinuz',
        '/boot/vmlinuz-5.14.0-354.el9.x86_64',
    ]

    uname_r = kernel_lib.get_uname_r_provided_by_kernel_pkg(
        kernel_nevra, context=_mock_context_for_file_list(kernel_nevra, file_lines)
    )
    assert uname_r == '5.14.0-354.el9.x86_64'


def test_get_uname_r_provided_by_kernel_pkg_default_context(monkeypatch):
    kernel_nevra = 'kernel-core-5.14.0-354.el9.x86_64'

    def run_mocked(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-q', '-l', kernel_nevra]
        return {'stdout': [
            '/lib/modules/5.14.0-354.el9.x86_64/vmlinuz'
        ]}

    monkeypatch.setattr(kernel_lib.mounting, 'run', run_mocked)

    uname_r = kernel_lib.get_uname_r_provided_by_kernel_pkg(kernel_nevra)
    assert uname_r == '5.14.0-354.el9.x86_64'


@pytest.mark.parametrize(
    ('uname_r', 'whatprovides_nevras', 'expected_nevra'),
    (
        ('5.14.0-354.el9.x86_64',
         ['kernel-modules-core-5.14.0-354.el9.x86_64', 'kernel-core-5.14.0-354.el9.x86_64'],
         'kernel-core-5.14.0-354.el9.x86_64'),
        ('5.14.0-354.el9.x86_64+rt',
         ['kernel-rt-modules-core-5.14.0-354.el9.x86_64', 'kernel-rt-core-5.14.0-354.el9.x86_64'],
         'kernel-rt-core-5.14.0-354.el9.x86_64'),
        ('5.14.0-687.el9.aarch64+64k',
         ['kernel-64k-modules-core-5.14.0-687.el9.aarch64', 'kernel-64k-core-5.14.0-687.el9.aarch64'],
         'kernel-64k-core-5.14.0-687.el9.aarch64'),
        ('5.14.0-687.el9.aarch64+rt-64k',
         ['kernel-rt-64k-modules-core-5.14.0-687.el9.aarch64', 'kernel-rt-64k-core-5.14.0-687.el9.aarch64'],
         'kernel-rt-64k-core-5.14.0-687.el9.aarch64'),
        ('unknown', None, None),
    )
)
def test_get_kernel_pkg_info_for_uname_r(monkeypatch, uname_r, whatprovides_nevras, expected_nevra):
    def run_mocked(cmd, *args, **kwargs):
        assert cmd[:3] == ['rpm', '-q', '--whatprovides']
        assert cmd[3] == '/lib/modules/{}'.format(uname_r)
        if whatprovides_nevras is None:
            raise CalledProcessError(
                message='rpm query failed', command=cmd,
                result={'exit_code': 1, 'stdout': '', 'stderr': ''})
        return {'stdout': whatprovides_nevras}

    def get_kernel_pkg_info_mocked(nevra):
        name = nevra.rsplit('-', 2)[0]
        return kernel_lib.KernelPkgInfo(name=name, version='', release='', arch='', nevra=nevra)

    monkeypatch.setattr(kernel_lib, 'run', run_mocked)
    monkeypatch.setattr(kernel_lib, 'get_kernel_pkg_info', get_kernel_pkg_info_mocked)

    if expected_nevra:
        pkg_info = kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)
        assert pkg_info.nevra == expected_nevra
        assert pkg_info.name.endswith('-core')
        assert '-modules' not in pkg_info.name
    else:
        with pytest.raises(kernel_lib.KernelPackageInfoError):
            kernel_lib.get_kernel_pkg_info_for_uname_r(uname_r)


@pytest.mark.parametrize(
    ('kernel_type', 'page_size', 'arch', 'expected'),
    (
        # 4k page size: standard packages on all architectures
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_4K, 'x86_64',
         ('kernel', 'kernel-core', 'kernel-modules')),
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_4K, 'aarch64',
         ('kernel', 'kernel-core', 'kernel-modules')),
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_4K, 'ppc64le',
         ('kernel', 'kernel-core', 'kernel-modules')),
        (KernelType.REALTIME, KernelPageSize.PAGE_SIZE_4K, 'x86_64',
         ('kernel-rt', 'kernel-rt-core', 'kernel-rt-modules')),
        # 64k page size on aarch64: 64k variant packages
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_64K, 'aarch64',
         ('kernel-64k', 'kernel-64k-core', 'kernel-64k-modules')),
        (KernelType.REALTIME, KernelPageSize.PAGE_SIZE_64K, 'aarch64',
         ('kernel-rt-64k', 'kernel-rt-64k-core', 'kernel-rt-64k-modules')),
        # 64k page size on non-aarch64: standard packages (no kernel-64k RPMs exist)
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_64K, 'ppc64le',
         ('kernel', 'kernel-core', 'kernel-modules')),
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_64K, 'x86_64',
         ('kernel', 'kernel-core', 'kernel-modules')),
        (KernelType.ORDINARY, KernelPageSize.PAGE_SIZE_64K, 's390x',
         ('kernel', 'kernel-core', 'kernel-modules')),
    )
)
def test_get_target_kernel_pkg_names(kernel_type, page_size, arch, expected):
    assert kernel_lib.get_target_kernel_pkg_names(kernel_type, page_size, arch) == expected
