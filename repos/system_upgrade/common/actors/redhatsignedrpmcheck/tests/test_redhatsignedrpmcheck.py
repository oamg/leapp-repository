from leapp import reporting
from leapp.libraries.actor import redhatsignedrpmcheck
from leapp.libraries.common.testutils import create_report_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledUnsignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_actor_execution_without_unsigned_data(monkeypatch):
    def consume_unsigned_message_mocked(*models):
        installed_rpm = []
        yield InstalledUnsignedRPM(items=installed_rpm)
    monkeypatch.setattr(api, "consume", consume_unsigned_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(api, "show_message", lambda x: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    packages = redhatsignedrpmcheck.get_unsigned_packages()
    assert not packages
    redhatsignedrpmcheck.generate_report(packages)
    assert reporting.create_report.called == 0


def test_actor_execution_with_unsigned_data(monkeypatch):
    def consume_unsigned_message_mocked(*models):
        installed_rpm = [
            RPM(name='sample02', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='SOME_OTHER_SIG_X'),
            RPM(name='sample04', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='SOME_OTHER_SIG_X'),
            RPM(name='sample06', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='SOME_OTHER_SIG_X'),
            RPM(name='sample08', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='SOME_OTHER_SIG_X')]
        yield InstalledUnsignedRPM(items=installed_rpm)

    monkeypatch.setattr(api, "consume", consume_unsigned_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(api, "show_message", lambda x: True)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    packages = redhatsignedrpmcheck.get_unsigned_packages()
    assert len(packages) == 4
    redhatsignedrpmcheck.generate_report(packages)
    assert reporting.create_report.called == 1
    assert 'Packages not signed by Red Hat found' in reporting.create_report.report_fields['title']
