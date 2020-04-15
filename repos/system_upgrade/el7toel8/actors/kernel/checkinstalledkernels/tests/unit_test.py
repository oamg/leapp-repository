from collections import namedtuple

from leapp import reporting
from leapp.libraries.actor import library
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


class mocked_logger(object):
    def __init__(self):
        self.errmsg = None

    def error(self, *args):
        self.errmsg = args

    def __call__(self):
        return self


def mocked_consume(pkgs):  # pkgs = [(name, version-number)]
    installed_rpms = []
    version = 1
    for pkg in pkgs:
        installed_rpms.append(RPM(
                name=pkg[0], arch='noarch',
                version=str(version), release='{}.sm01'.format(pkg[1]), epoch='0',
                packager=RH_PACKAGER, pgpsig='SOME_OTHER_SIG_X'))
        version += 1

    def f(*a):
        yield InstalledRedHatSignedRPM(items=installed_rpms)
    return f


s390x_pkgs_single = [('kernel', 957), ('something', 957), ('kernel-something', 957)]
s390x_pkgs_multi = [('kernel', 957), ('something', 957), ('kernel', 956)]


def test_single_kernel_s390x(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_single))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_single))
    library.process()
    assert not reporting.create_report.called


def test_multi_kernel_s390x(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_multi))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch=architecture.ARCH_S390X))
    monkeypatch.setattr(api, 'consume', mocked_consume(s390x_pkgs_multi))
    library.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Multiple kernels installed'


versioned_kernel_pkgs = [('kernel', 456), ('kernel', 789), ('kernel', 1234)]


def test_newest_kernel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-1234.21.1.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-456.43.1.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(kernel='3.10.0-789.35.2.el7.x86_64'))
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, 'consume', mocked_consume(versioned_kernel_pkgs))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Newest installed kernel not in use'
