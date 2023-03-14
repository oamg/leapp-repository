import leapp.libraries.actor.checkmicroarchitecture as checkmicroarchitecture
from leapp.actors import Actor
from leapp.models import CPUInfo
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckMicroarchitecture(Actor):
    """
    Inhibit if RHEL9 microarchitecture requirements are not satisfied


    As per `x86-64-ABI`_ In addition to the AMD64 baseline architecture, several
    micro-architecture levels implemented by later CPU modules have been
    defined, starting at level ``x86-64-v2``. The levels are cumulative in the
    sense that features from previous levels are implicitly included in later
    levels.

    RHEL9 has a higher CPU requirement than older versions, it now requires a
    CPU compatible with ``x86-64-v2`` instruction set or higher.

    .. table:: Required CPU features by microarchitecure level with a
               corresponding flag as shown by ``lscpu``.

        +------------+-------------+--------------------+
        | Version    | CPU Feature | flag (lscpu)       |
        +============+=============+====================+
        | (baseline) | CMOV        | cmov               |
        |            | CX8         | cx8                |
        |            | FPU         | fpu                |
        |            | FXSR        | fxsr               |
        |            | MMX         | mmx                |
        |            | OSFXSR      | (common with FXSR) |
        |            | SCE         | syscall            |
        |            | SSE         | sse                |
        |            | SSE2        | sse2               |
        +------------+-------------+--------------------+
        | x86-64-v2  | CMPXCHG16B  | cx16               |
        |            | LAHF-SAHF   | lahf_lm            |
        |            | POPCNT      | popcnt             |
        |            | SSE3        | pni                |
        |            | SSE4_1      | sse4_1             |
        |            | SSE4_2      | sse4_2             |
        |            | SSSE3       | ssse3              |
        +------------+-------------+--------------------+
        | ...        |             |                    |
        +------------+-------------+--------------------+

    Note: To get the corresponding flag for the CPU feature consult the file
    ``/arch/x86/include/asm/cpufeatures.h`` in the linux kernel.


    .. _x86-64-ABI: https://gitlab.com/x86-psABIs/x86-64-ABI.git

    """

    name = 'check_microarchitecture'
    consumes = (CPUInfo,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        checkmicroarchitecture.process()
