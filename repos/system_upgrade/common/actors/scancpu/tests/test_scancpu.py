import os

from leapp.libraries.actor import scancpu
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


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


def test_machine_type(monkeypatch):

    # cpuinfo doesn't contain a machine field
    mocked_cpuinfo = mocked_get_cpuinfo('lscpu_x86_64')
    monkeypatch.setattr(scancpu, '_get_lscpu_output', mocked_cpuinfo)
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    current_actor = testutils.CurrentActorMocked(arch=testutils.architecture.ARCH_X86_64)
    monkeypatch.setattr(api, 'current_actor', current_actor)
    scancpu.process()
    assert api.produce.called == 1
    assert CPUInfo() == api.produce.model_instances[0]

    # cpuinfo contains a machine field
    api.produce.called = 0
    api.produce.model_instances = []
    current_actor = testutils.CurrentActorMocked(arch=testutils.architecture.ARCH_S390X)
    monkeypatch.setattr(api, 'current_actor', current_actor)
    mocked_cpuinfo.filename = 'lscpu_s390x'
    scancpu.process()
    assert api.produce.called == 1
    assert CPUInfo(machine_type=2827) == api.produce.model_instances[0]
