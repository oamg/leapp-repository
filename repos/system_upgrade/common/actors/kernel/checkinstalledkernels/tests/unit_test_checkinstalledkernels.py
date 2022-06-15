import pytest

from leapp import reporting
from leapp.libraries.actor import checkinstalledkernels
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

# Do not make sense to run any tests when the module is not accessible
pytest.importorskip("rpm")


def create_rpm(
            version,
            release,
            name='kernel',
            packager=RH_PACKAGER,
            pgpsig='SOME_OTHER_SIG_X',
            epoch='0',
            ):
    return RPM(
        name=name,
        arch=release.split('.')[-1],
        version=version,
        release='.'.join(release.split('.')[0:-1]),
        epoch='0',
        packager=RH_PACKAGER,
        pgpsig='SOME_OTHER_SIG_X',
    )


def create_rpms(pkgs):
    installed_rpms = InstalledRedHatSignedRPM()
    for pkg in pkgs:
        installed_rpms.items.append(
            create_rpm(name=pkg[0], version=pkg[1], release=pkg[2]))
    return installed_rpms


@pytest.mark.parametrize('vra,version,release', [
    ('3.10.0-1234.21.1.el7.x86_64', '3.10.0', '1234.21.1.el7.x86_64'),
    ('5.8.8-100.fc31.x86_64', '5.8.8', '100.fc31.x86_64'),
])
def test_current_kernel(monkeypatch, vra, version, release):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=vra))
    assert version == checkinstalledkernels.get_current_kernel_version()
    assert release == checkinstalledkernels.get_current_kernel_release()


s390x_pkgs_single = [
    ('kernel', '3.10.0', '957.43.1.el7.s390x'),
    ('something', '3.10.0', '957.43.1.el7.s390x'),
    ('kernel-something', '3.10.0', '957.43.1.el7.s390x')
]
s390x_pkgs_multi = [
    ('kernel', '3.10.0', '957.43.1.el7.s390x'),
    ('something', '3.10.0', '957.43.1.el7.s390x'),
    ('kernel', '3.10.0', '956.43.1.el7.s390x')
]


def test_single_kernel_s390x(monkeypatch):
    msgs = [create_rpms(s390x_pkgs_single)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch=architecture.ARCH_S390X,
        msgs=msgs,
        kernel='3.10.0-957.43.1.el7.s390x'),
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert not reporting.create_report.called


def test_multi_kernel_s390x(monkeypatch):
    msgs = [create_rpms(s390x_pkgs_multi)]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch=architecture.ARCH_S390X,
        msgs=msgs,
        kernel='3.10.0-957.43.1.el7.s390x'),
    )
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Multiple kernels installed'


versioned_kernel_pkgs = [
    ('kernel', '3.10.0', '456.43.1.el7.x86_64'),
    ('kernel', '3.10.0', '789.35.2.el7.x86_64'),
    ('kernel', '3.10.0', '1234.21.1.el7.x86_64')
]


@pytest.mark.parametrize('expect_report,msgs,curr_kernel', [
    (False, [create_rpms(versioned_kernel_pkgs)], '3.10.0-1234.21.1.el7.x86_64'),
    (True, [create_rpms(versioned_kernel_pkgs)], '3.10.0-456.43.1.el7.x86_64'),
    (True, [create_rpms(versioned_kernel_pkgs)], '3.10.0-789.35.2.el7.x86_64'),
])
def test_newest_kernel(monkeypatch, expect_report, msgs, curr_kernel):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=curr_kernel, msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    if expect_report:
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
    else:
        assert not reporting.create_report.called


# put the kernel in the middle of the list so that its position doesn't guarantee its rank
versioned_kernel_pkgs.insert(2, ('kernel', '4.14.0', '115.29.1.el7.x86_64'))


@pytest.mark.parametrize('expect_report,msgs,curr_kernel', [
    (True, [create_rpms(versioned_kernel_pkgs)], '3.10.0-1234.21.1.el7.x86_64'),
    (False, [create_rpms(versioned_kernel_pkgs)], '4.14.0-115.29.1.el7.x86_64'),
])
def test_newest_kernel_more_versions(monkeypatch, expect_report, msgs, curr_kernel):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=curr_kernel, msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    if expect_report:
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
    else:
        assert not reporting.create_report.called


@pytest.mark.parametrize('evr', [
    ('', '3.10.0', '1234.21.1.el7.x86_64'),
    ('', '3.10.0', '456.43.1.el7.x86_64'),
    ('', '3.10.0', '1.1.1.1.1.1.1.2.el7x86_64'),
    ('', '4.10.4', '1234.21.1.el7.x86_64'),
    ('', '6.6.6', '1234.56.rt78.el9.x86_64'),
])
def test_get_evr(monkeypatch, evr):
    pkg = create_rpm(version=evr[1], release=evr[2])
    assert checkinstalledkernels.get_EVR(pkg) == evr


versioned_kernel_rt_pkgs = [
    ('kernel-rt', '3.10.0', '789.35.2.rt56.1133.el7.x86_64'),
    ('kernel-rt', '3.10.0', '789.35.2.rt57.1133.el7.x86_64'),
    ('kernel-rt', '3.10.0', '789.35.2.rt101.1133.el7.x86_64'),
    ('kernel-rt', '3.10.0', '790.35.2.rt666.1133.el7.x86_64'),
]


@pytest.mark.parametrize('msgs,num,name', [
    ([create_rpms(versioned_kernel_rt_pkgs)], 4, 'kernel-rt'),
    ([create_rpms(versioned_kernel_rt_pkgs[0:-1])], 3, 'kernel-rt'),
    ([create_rpms(versioned_kernel_rt_pkgs[0:-2])], 2, 'kernel-rt'),
    ([create_rpms(versioned_kernel_rt_pkgs[0:-3])], 1, 'kernel-rt'),
    ([create_rpms(versioned_kernel_rt_pkgs)], 0, 'kernel'),
    ([create_rpms(versioned_kernel_rt_pkgs)], 0, 'smth'),
    ([create_rpms(versioned_kernel_pkgs)], 0, 'kernel-rt'),
    ([create_rpms(versioned_kernel_pkgs + versioned_kernel_rt_pkgs)], 4, 'kernel-rt'),
    ([create_rpms(versioned_kernel_pkgs + versioned_kernel_rt_pkgs)], 4, 'kernel'),
])
def test_get_pkgs(monkeypatch, msgs, num, name):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    pkgs = checkinstalledkernels.get_pkgs(name)
    assert len(pkgs) == num


@pytest.mark.parametrize('expect_report,msgs,curr_kernel', [
    # kernel-rt only
    (True, [create_rpms(versioned_kernel_rt_pkgs)], '3.10.0-789.35.2.rt56.1133.el7.x86_64'),
    (True, [create_rpms(versioned_kernel_rt_pkgs)], '3.10.0-789.35.2.rt57.1133.el7.x86_64'),
    (True, [create_rpms(versioned_kernel_rt_pkgs)], '3.10.0-789.35.2.rt101.1133.el7.x86_64'),
    (False, [create_rpms(versioned_kernel_rt_pkgs)], '3.10.0-790.35.2.rt666.1133.el7.x86_64'),
    (False, [create_rpms(versioned_kernel_rt_pkgs[0:-1])], '3.10.0-789.35.2.rt101.1133.el7.x86_64'),
    (False, [create_rpms(versioned_kernel_rt_pkgs[0:1])], '3.10.0-789.35.2.rt56.1133.el7.x86_64'),

    # mix of kernel-rt + kernel
    (
        True,
        [create_rpms(versioned_kernel_rt_pkgs + versioned_kernel_pkgs)],
        '3.10.0-789.35.2.rt101.1133.el7.x86_64'
    ),
    (
        False,
        [create_rpms(versioned_kernel_rt_pkgs + versioned_kernel_pkgs)],
        '3.10.0-790.35.2.rt666.1133.el7.x86_64'
    ),
    (
        True,
        [create_rpms(versioned_kernel_rt_pkgs + versioned_kernel_pkgs)],
        '3.10.0-1234.21.1.el7.x86_64'
    ),
    (
        False,
        [create_rpms(versioned_kernel_rt_pkgs + versioned_kernel_pkgs)],
        '4.14.0-115.29.1.el7.x86_64'
    ),
])
def test_newest_kernel_realtime(monkeypatch, expect_report, msgs, curr_kernel):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=curr_kernel, msgs=msgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    if expect_report:
        assert reporting.create_report.called
        assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
    else:
        assert not reporting.create_report.called


@pytest.mark.parametrize('current_actor_mocked,expected_name', [
    (CurrentActorMocked(kernel='3.10.0-957.43.1.el7.x86_64', src_ver='7.9'), 'kernel'),
    (CurrentActorMocked(kernel='3.10.0-789.35.2.rt56.1133.el7.x86_64', src_ver='7.9'), 'kernel-rt'),
    (CurrentActorMocked(kernel='4.14.0-115.29.1.el7.x86_64', src_ver='8.6'), 'kernel-core'),
    (CurrentActorMocked(kernel='4.14.0-789.35.2.rt56.1133.el8.x86_64', src_ver='8.6'), 'kernel-rt-core'),
])
def test_kernel_name(monkeypatch, current_actor_mocked, expected_name):
    monkeypatch.setattr(api, 'current_actor', current_actor_mocked)
    assert expected_name == checkinstalledkernels._get_kernel_rpm_name()
