from collections import namedtuple

from leapp import reporting
from leapp.libraries.actor import library
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


class CurrentActorMocked(object):
    def __init__(self, arch):
        self.configuration = namedtuple('configuration', ['architecture'])(arch)

    def __call__(self):
        return self


class mocked_logger(object):
    def __init__(self):
        self.errmsg = None

    def error(self, *args):
        self.errmsg = args

    def __call__(self):
        return self


def mocked_consume(pkg_names):
    installed_rpms = []
    version = 1
    for pkg in pkg_names:
        installed_rpms.append(RPM(
                name=pkg, arch='noarch',
                version=str(version), release='1.sm01', epoch='0',
                packager=RH_PACKAGER, pgpsig='SOME_OTHER_SIG_X'))
        version += 1

    def f(*a):
        yield InstalledRedHatSignedRPM(items=installed_rpms)
    return f


def test_single_kernel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, "consume", mocked_consume(['kernel', 'someting', 'kernel-somethin']))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    library.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    monkeypatch.setattr(api, "consume", mocked_consume(['kernel', 'someting', 'kernel-somethin']))
    library.process()
    assert not reporting.create_report.called


def test_multi_kernel(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(api, 'current_logger', mocked_logger())
    monkeypatch.setattr(api, "consume", mocked_consume(['kernel', 'someting', 'kernel']))
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    library.process()
    assert not reporting.create_report.called

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    monkeypatch.setattr(api, "consume", mocked_consume(['kernel', 'someting', 'kernel']))
    library.process()
    assert reporting.create_report.called
    assert reporting.create_report.report_fields['title'] == 'Multiple kernels installed'
