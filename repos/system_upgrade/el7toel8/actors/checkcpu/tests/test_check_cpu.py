from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import cpu
from leapp.libraries.common import testutils
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo


class CurrentActorMocked(object):
    def __init__(self, arch):
        self.configuration = namedtuple('configuration', ['architecture'])(arch)

    def __call__(self):
        return self


def test_non_ibmz_arch(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    cpu.process()
    assert not reporting.create_report.called


def test_ibmz_arch_missing_cpuinfo(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    monkeypatch.setattr(api, 'consume', lambda x: iter([]))
    with pytest.raises(StopActorExecutionError):
        cpu.process()
    assert not reporting.create_report.called


def test_ibmz_cpu_supported(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    for sup_arch in cpu.SUPPORTED_MACHINE_TYPES:
        monkeypatch.setattr(api, 'consume', lambda x: iter([CPUInfo(machine_type=sup_arch)]))
        cpu.process()
        assert not reporting.create_report.called


def test_ibmz_cpu_unsupported(monkeypatch):
    title_msg = 'The processor is not supported by the target system.'
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_S390X))
    monkeypatch.setattr(api, 'consume', lambda x: iter([CPUInfo(machine_type=666)]))
    monkeypatch.setattr(reporting, "create_report", testutils.create_report_mocked())
    cpu.process()
    assert reporting.create_report.called
    assert title_msg == reporting.create_report.report_fields['title']
    assert reporting.Flags.INHIBITOR in reporting.create_report.report_fields['flags']
