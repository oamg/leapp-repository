import os

import pytest

from leapp.libraries.actor import scancpu
from leapp.libraries.common import testutils
from leapp.libraries.common.config.architecture import (
    ARCH_ARM64,
    ARCH_PPC64LE,
    ARCH_S390X,
    ARCH_SUPPORTED,
    ARCH_X86_64
)
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

CUR_DIR = os.path.dirname(os.path.abspath(__file__))

LSCPU = {
    ARCH_ARM64: {
        "machine_type": None,
        "flags": ['fp', 'asimd', 'evtstrm', 'aes', 'pmull', 'sha1', 'sha2', 'crc32', 'cpuid'],
    },
    ARCH_PPC64LE: {
        "machine_type": None,
        "flags": []
    },
    ARCH_S390X: {
        "machine_type":
            2827,
        "flags": [
            'esan3', 'zarch', 'stfle', 'msa', 'ldisp', 'eimm', 'dfp', 'edat', 'etf3eh', 'highgprs', 'te', 'vx', 'vxd',
            'vxe', 'gs', 'vxe2', 'vxp', 'sort', 'dflt', 'sie'
        ]
    },
    ARCH_X86_64: {
        "machine_type":
            None,
        "flags": [
            'fpu', 'vme', 'de', 'pse', 'tsc', 'msr', 'pae', 'mce', 'cx8', 'apic', 'sep', 'mtrr', 'pge', 'mca', 'cmov',
            'pat', 'pse36', 'clflush', 'dts', 'acpi', 'mmx', 'fxsr', 'sse', 'sse2', 'ss', 'ht', 'tm', 'pbe', 'syscall',
            'nx', 'pdpe1gb', 'rdtscp', 'lm', 'constant_tsc', 'arch_perfmon', 'pebs', 'bts', 'rep_good', 'nopl',
            'xtopology', 'nonstop_tsc', 'cpuid', 'aperfmperf', 'pni', 'pclmulqdq', 'dtes64', 'monitor', 'ds_cpl',
            'vmx', 'smx', 'est', 'tm2', 'ssse3', 'sdbg', 'fma', 'cx16', 'xtpr', 'pdcm', 'pcid', 'dca', 'sse4_1',
            'sse4_2', 'x2apic', 'movbe', 'popcnt', 'tsc_deadline_timer', 'aes', 'xsave', 'avx', 'f16c', 'rdrand',
            'lahf_lm', 'abm', 'cpuid_fault', 'epb', 'invpcid_single', 'pti', 'ssbd', 'ibrs', 'ibpb', 'stibp',
            'tpr_shadow', 'vnmi', 'flexpriority', 'ept', 'vpid', 'ept_ad', 'fsgsbase', 'tsc_adjust', 'bmi1', 'avx2',
            'smep', 'bmi2', 'erms', 'invpcid', 'cqm', 'xsaveopt', 'cqm_llc', 'cqm_occup_llc', 'dtherm', 'ida', 'arat',
            'pln', 'pts', 'md_clear', 'flush_l1d'
        ]
    },
}


class mocked_get_cpuinfo(object):

    def __init__(self, filename):
        self.filename = filename

    def __call__(self):
        """
        Return lines of the self.filename test file located in the files directory.

        Those files contain /proc/cpuinfo content from several machines.
        """
        with open(os.path.join(CUR_DIR, 'files', self.filename), 'r') as fp:
            return '\n'.join(fp.read().splitlines())


@pytest.mark.parametrize("arch", ARCH_SUPPORTED)
def test_scancpu(monkeypatch, arch):

    mocked_cpuinfo = mocked_get_cpuinfo('lscpu_' + arch)
    monkeypatch.setattr(scancpu, '_get_lscpu_output', mocked_cpuinfo)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    current_actor = testutils.CurrentActorMocked(arch=arch)
    monkeypatch.setattr(api, 'current_actor', current_actor)

    scancpu.process()

    expected = CPUInfo(machine_type=LSCPU[arch]["machine_type"], flags=LSCPU[arch]["flags"])
    produced = api.produce.model_instances[0]

    assert api.produce.called == 1

    # Produced what was expected
    assert expected.machine_type == produced.machine_type
    assert sorted(expected.flags) == sorted(produced.flags)

    # Did not produce anything extra
    assert expected == produced
