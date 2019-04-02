import os

import pytest
from leapp.exceptions import StopActorExecution
from leapp.libraries.actor import library
from leapp.libraries.common import reporting
from leapp.libraries.stdlib import api
from leapp.models import RPM, InstalledUnsignedRPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


class produce_mocked(object):
    def __init__(self):
        self.called = 0
        self.model_instances = []

    def __call__(self, *model_instances):
        self.called += 1
        self.model_instances.append(model_instances[0])


class report_generic_mocked(object):
    def __init__(self):
        self.called = 0

    def __call__(self, **report_fields):
        self.called += 1
        self.report_fields = report_fields


def test_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda(_): True)
    monkeypatch.setattr(reporting, "report_generic", report_generic_mocked())
    with pytest.raises(StopActorExecution):
        library.skip_check()
    assert reporting.report_generic.called == 1
    assert 'Skipped signed packages check' in reporting.report_generic.report_fields['title']


def test_no_skip_check(monkeypatch):
    monkeypatch.setattr(os, "getenv", lambda(_): False)
    monkeypatch.setattr(reporting, "report_generic", report_generic_mocked())

    library.skip_check()
    assert reporting.report_generic.called == 0


def test_actor_execution_without_unsigned_data(monkeypatch):
    def consume_unsigned_message_mocked(*models):
        installed_rpm = []
        yield InstalledUnsignedRPM(items=installed_rpm)
    monkeypatch.setattr(api, "consume", consume_unsigned_message_mocked)
    monkeypatch.setattr(api, "produce", produce_mocked())
    monkeypatch.setattr(reporting, "report_with_remediation", report_generic_mocked())

    packages = library.get_unsigned_packages()
    assert len(packages) == 0
    library.generate_report(packages)
    assert reporting.report_with_remediation.called == 0


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
    monkeypatch.setattr(reporting, "report_with_remediation", report_generic_mocked())

    packages = library.get_unsigned_packages()
    assert len(packages) == 4
    library.generate_report(packages)
    assert reporting.report_with_remediation.called == 1
    assert 'Packages not signed by Red Hat found' in reporting.report_with_remediation.report_fields['title']
    assert 'yum remove sample' in reporting.report_with_remediation.report_fields['remediation']
