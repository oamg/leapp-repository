import pytest

from leapp import reporting
from leapp.libraries.actor import checkinstalledkernels
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import RPM, InstalledRedHatSignedRPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def mocked_consume(pkgs):  # pkgs = [(name, version-number)]
    installed_rpms = []
    for pkg in pkgs:
        installed_rpms.append(
            RPM(
                name=pkg[0],
                arch='noarch',
                version=pkg[1],
                release='{}.sm01'.format(pkg[2]),
                epoch='0',
                packager=RH_PACKAGER,
                pgpsig='SOME_OTHER_SIG_X',
            )
        )

    def f(*a):
        yield InstalledRedHatSignedRPM(items=installed_rpms)

    return f


@pytest.mark.parametrize('version,expected', [
    ([], [0, 0, 0]),
    ([1], [1, 0, 0]),
    ([1, 2], [1, 2, 0]),
    ([1, 2, 3], [1, 2, 3]),
    ([1, 2, 3, 4], [1, 2, 3]),
    ([1, 2, 3, 4, 5], [1, 2, 3])
])
def test_normalize(version, expected):
    assert checkinstalledkernels._normalize_version(version) == expected


@pytest.mark.parametrize('vra,version,release', [
    ('3.10.0-1234.21.1.el7.x86_64', (3, 10, 0), 1234),
    ('5.8.8-100.fc31.x86_64', (5, 8, 8), 100),
])
def test_current_kernel(monkeypatch, vra, version, release):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel=vra))
    assert version == checkinstalledkernels.get_current_kernel_version()
    assert release == checkinstalledkernels.get_current_kernel_release()


@pytest.mark.parametrize('version_string, release_string, version, release', [
    ('3.10.0', '1234.21.1.el7', (3, 10, 0), 1234),
    ('5.8.8', '100.fc31', (5, 8, 8), 100),
])
def test_kernel_rpm(version_string, release_string, version, release):
    rpm = RPM(
        name='kernel',
        arch='noarch',
        version=version_string,
        release=release_string,
        epoch='0',
        packager=RH_PACKAGER,
        pgpsig='SOME_OTHER_SIG_X',
    )
    assert version == checkinstalledkernels.get_kernel_rpm_version(rpm)
    assert release == checkinstalledkernels.get_kernel_rpm_release(rpm)


s390x_pkgs_single = [('kernel', '3.10.0', 957), ('something', '3.10.0', 957), ('kernel-something', '3.10.0', 957)]
s390x_pkgs_multi = [('kernel', '3.10.0', 957), ('something', '3.10.0', 957), ('kernel', '3.10.0', 956)]


def test_single_kernel_s390x(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_single))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_single))
    checkinstalledkernels.process()
    assert not reporting.create_report.called


def test_multi_kernel_s390x(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_multi))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_multi))
    checkinstalledkernels.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Multiple kernels installed'


versioned_kernel_pkgs = [('kernel', '3.10.0', 456), ('kernel', '3.10.0', 789), ('kernel', '3.10.0', 1234)]


def test_newest_kernel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-1234.21.1.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-456.43.1.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-789.35.2.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'

    # put the kernel in the middle of the list so that its position doesn't guarantee its rank
    versioned_kernel_pkgs.insert(2, ('kernel', '4.14.0', 115))

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='4.14.0-115.29.1.el7a.ppc64le'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-1234.21.1.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    checkinstalledkernels.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
