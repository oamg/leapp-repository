from collections import namedtuple

import pytest

from leapp import reporting
from leapp.libraries.actor import checkinstalledkernels
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, KernelInfo, RPM
from leapp.utils.report import is_inhibitor

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

# Does not make sense to run any tests when the module is not accessible
pytest.importorskip("rpm")


# Partial RPM description, missing fields are filled with defaults
RPMDesc = namedtuple('RPMDesc', ('name', 'version', 'release', 'arch'))


def create_rpm(rpm_desc, packager=RH_PACKAGER, pgpsig='SOME_OTHER_SIG_X', epoch='0'):
    return RPM(name=rpm_desc.name, arch=rpm_desc.arch, version=rpm_desc.version, release=rpm_desc.release,
               epoch='0', packager=RH_PACKAGER, pgpsig='SOME_OTHER_SIG_X')


def create_rpms(rpm_descriptions):
    rpms = [create_rpm(rpm_desc) for rpm_desc in rpm_descriptions]
    installed_rpms = DistributionSignedRPM(items=rpms)
    return installed_rpms


_UEK_KERNELS = [
    '5.15.0-100.96.32.el8uek.x86_64',
    '5.15.0-200.136.2.el9uek.aarch64',
]

_NON_UEK_KERNELS = [
    '4.18.0-513.5.1.el8.x86_64',
    '5.14.0-362.8.1.el9.x86_64',
]


def _create_uek_kernel_info(uname_r):
    """Create a KernelInfo message with a UEK uname_r."""
    pkg = RPM(
        name='kernel-uek',
        epoch='0',
        version='5.15.0',
        release='100.96.32.el8uek',
        arch='x86_64',
        packager='Oracle America',
        pgpsig='SOME_SIG',
    )
    return KernelInfo(pkg=pkg, uname_r=uname_r)


@pytest.mark.parametrize('uname_r', _UEK_KERNELS)
def test_inhibits_on_uek_kernel_during_conversion(monkeypatch, uname_r):
    kernel_info = _create_uek_kernel_info(uname_r)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[kernel_info]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkinstalledkernels, 'is_conversion', lambda: True)

    checkinstalledkernels.process()

    assert reporting.create_report.called == 1
    assert is_inhibitor(reporting.create_report.report_fields)
    assert 'UEK' in reporting.create_report.report_fields['title']


@pytest.mark.parametrize('uname_r', _UEK_KERNELS)
def test_no_uek_inhibitor_outside_conversion(monkeypatch, uname_r):
    """UEK check should not fire when not in conversion mode."""
    installed_rpms = create_rpms([
        RPMDesc(name='kernel-uek', version='5.15.0', release='100.96.32.el8uek', arch='x86_64'),
    ])
    kernel_info = _create_uek_kernel_info(uname_r)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[kernel_info, installed_rpms]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkinstalledkernels, 'is_conversion', lambda: False)

    checkinstalledkernels.process()

    assert not reporting.create_report.called


@pytest.mark.parametrize('uname_r', _NON_UEK_KERNELS)
def test_no_uek_inhibitor_on_regular_kernel(monkeypatch, uname_r):
    """Non-UEK kernels should not trigger the UEK inhibitor even during conversion."""
    installed_rpms = create_rpms([
        RPMDesc(name='kernel', version='5.14.0', release='362.8.1.el9', arch='x86_64'),
    ])
    kernel_info = KernelInfo(pkg=installed_rpms.items[0], uname_r=uname_r)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[kernel_info, installed_rpms]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(checkinstalledkernels, 'is_conversion', lambda: True)

    checkinstalledkernels.process()

    assert not reporting.create_report.called


s390x_pkgs_single = [
    RPMDesc(name='kernel', version='3.10.0', release='957.43.1.el7', arch='s390x'),
    RPMDesc(name='something', version='3.10.0', release='957.43.1.el7', arch='s390x'),
    RPMDesc(name='kernel-something', version='3.10.0', release='957.43.1.el7', arch='s390x'),
]
s390x_pkgs_multi = [
    RPMDesc(name='kernel', version='3.10.0', release='957.43.1.el7', arch='s390x'),
    RPMDesc(name='something', version='3.10.0', release='957.43.1.el7', arch='s390x'),
    RPMDesc(name='kernel', version='3.10.0', release='956.43.1.el7', arch='s390x')
]


@pytest.mark.parametrize(
    ('pkgs', 'should_inhibit'),  # First tuple in pkgs is expected to provide the booted kernel
    (
        (s390x_pkgs_single, False),
        (s390x_pkgs_multi, True)
    )
)
def test_s390x_kernel_count_inhibition(monkeypatch, pkgs, should_inhibit):
    installed_rpms_msg = create_rpms(pkgs)
    kernel_pkg = installed_rpms_msg.items[0]
    kernel_info = KernelInfo(pkg=kernel_pkg, uname_r='957.43.1.el7.s390x')

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X,
                                                                 msgs=[kernel_info, installed_rpms_msg]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert should_inhibit == bool(reporting.create_report.called)


versioned_kernel_pkgs = [
    RPMDesc(name='kernel', version='3.10.0', release='789.35.2.el7', arch='x86_64'),
    RPMDesc(name='kernel', version='3.10.0', release='1234.21.1.el7', arch='x86_64'),
    RPMDesc(name='kernel', version='4.14.0', release='115.29.1.el7', arch='x86_64'),  # [2] - newest
    RPMDesc(name='kernel', version='3.10.0', release='456.43.1.el7', arch='x86_64'),
]


@pytest.mark.parametrize(
    ('expect_report', 'installed_rpms_msg', 'current_kernel_pkg_index'),
    (
        (False, create_rpms(versioned_kernel_pkgs), 2),
        (True, create_rpms(versioned_kernel_pkgs), 1),
        (True, create_rpms(versioned_kernel_pkgs), 0),
    )
)
def test_newest_kernel(monkeypatch, expect_report, installed_rpms_msg, current_kernel_pkg_index):
    uname_r = ''  # Kernel release is not used to determine the kernel novelty
    kernel_info = KernelInfo(pkg=installed_rpms_msg.items[current_kernel_pkg_index], uname_r=uname_r)
    msgs = [installed_rpms_msg, kernel_info]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    if expect_report:
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
    else:
        assert not reporting.create_report.called


@pytest.mark.parametrize(
    'rpm_desc',
    [
        RPMDesc(name='', version='3.10.0', release='1234.21.1.el7', arch='x86_64'),
        RPMDesc(name='', version='3.10.0', release='456.43.1.el7', arch='x86_64'),
        RPMDesc(name='', version='3.10.0', release='1.1.1.1.1.1.1.2', arch='x86_64'),
        RPMDesc(name='', version='4.10.4', release='1234.21.1.el7', arch='x86_64'),
        RPMDesc(name='', version='6.6.6', release='1234.56.rt78.el9', arch='x86_64'),
    ]
)
def test_get_evr(monkeypatch, rpm_desc):
    pkg = create_rpm(rpm_desc)
    assert checkinstalledkernels.get_EVR(pkg) == ('', pkg.version, pkg.release)


versioned_kernel_rt_pkgs = [
    RPMDesc(name='kernel-rt', version='3.10.0', release='789.35.2.rt56.1133.el7', arch='x86_64'),
    RPMDesc(name='kernel-rt', version='3.10.0', release='789.35.2.rt57.1133.el7', arch='x86_64'),
    RPMDesc(name='kernel-rt', version='3.10.0', release='789.35.2.rt101.1133.el7', arch='x86_64'),
    RPMDesc(name='kernel-rt', version='3.10.0', release='790.35.2.rt666.1133.el7', arch='x86_64'),  # [3] - newest
]


@pytest.mark.parametrize(
    ('msgs', 'num', 'name'),
    [
        ([create_rpms(versioned_kernel_rt_pkgs)], 4, 'kernel-rt'),
        ([create_rpms(versioned_kernel_rt_pkgs[0:-1])], 3, 'kernel-rt'),
        ([create_rpms(versioned_kernel_rt_pkgs[0:-2])], 2, 'kernel-rt'),
        ([create_rpms(versioned_kernel_rt_pkgs[0:-3])], 1, 'kernel-rt'),
        ([create_rpms(versioned_kernel_rt_pkgs)], 0, 'kernel'),
        ([create_rpms(versioned_kernel_rt_pkgs)], 0, 'smth'),
        ([create_rpms(versioned_kernel_pkgs)], 0, 'kernel-rt'),
        ([create_rpms(versioned_kernel_pkgs + versioned_kernel_rt_pkgs)], 4, 'kernel-rt'),
        ([create_rpms(versioned_kernel_pkgs + versioned_kernel_rt_pkgs)], 4, 'kernel'),
    ]
)
def test_get_pkgs(monkeypatch, msgs, num, name):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    pkgs = checkinstalledkernels.get_all_pkgs_with_name(name)
    assert len(pkgs) == num


mixed_kernel_pkgs = create_rpms(versioned_kernel_rt_pkgs + versioned_kernel_pkgs)
mixed_kernel_pkgs_desc_table = {  # Maps important pkgs from mixed_kernel_pkgs to their index so they can be ref'd
    'newest_rt': 3,
    'older_rt': 2,
    'newest_ordinary': 6,
    'older_ordinary': 5,
}


@pytest.mark.parametrize(
    ('expect_report', 'installed_rpms_msg', 'curr_kernel_pkg_index'),
    [
        # kernel-rt only
        (True, create_rpms(versioned_kernel_rt_pkgs), 0),
        (True, create_rpms(versioned_kernel_rt_pkgs), 1),
        (True, create_rpms(versioned_kernel_rt_pkgs), 2),
        (False, create_rpms(versioned_kernel_rt_pkgs), 3),  # newest
        (False, create_rpms(versioned_kernel_rt_pkgs[0:-1]), 2),
        (False, create_rpms(versioned_kernel_rt_pkgs[0:1]), 0),

        # mix of kernel-rt + kernel
        (True, mixed_kernel_pkgs, mixed_kernel_pkgs_desc_table['older_rt']),
        (False, mixed_kernel_pkgs, mixed_kernel_pkgs_desc_table['newest_rt']),
        (True, mixed_kernel_pkgs, mixed_kernel_pkgs_desc_table['older_ordinary']),
        (False, mixed_kernel_pkgs, mixed_kernel_pkgs_desc_table['newest_ordinary']),
    ]
)
def test_newest_kernel_realtime(monkeypatch, expect_report, installed_rpms_msg, curr_kernel_pkg_index):
    current_kernel_pkg = installed_rpms_msg.items[curr_kernel_pkg_index]
    kernel_info = KernelInfo(pkg=current_kernel_pkg, uname_r='')
    msgs = [installed_rpms_msg, kernel_info]

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()

    if expect_report:
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
    else:
        assert not reporting.create_report.called
