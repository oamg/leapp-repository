from leapp.actors import Actor
from leapp.libraries.actor import cpu
from leapp.models import CPUInfo, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckCPU(Actor):
    """
    Check whether the CPU is supported by the target system. Inhibit upgrade if not.

    Currently we know just about cases with s390x where the set of CPUs supported
    by RHEL 8 is subset of CPUs supported on RHEL 7. We can detect such cases based
    on the machine field inside the /proc/cpuinfo file. expected values of the
    field on supported machines are: 2964, 2965, 3906, 3907, 8561, 8562.
    """

    name = "checkcpu"
    consumes = (CPUInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        cpu.process()
