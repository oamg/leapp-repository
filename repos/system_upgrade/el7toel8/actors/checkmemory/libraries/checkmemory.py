from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import MemoryInfo

min_req_memory = {
    architecture.ARCH_X86_64: 1536,  # 1.5G
    architecture.ARCH_ARM64: 2048,  # 2Gb
    architecture.ARCH_PPC64LE: 2048,  # 2Gb
    architecture.ARCH_S390X: 1024  # 1Gb
}


def _check_memory(mem_info):
    msg = {}

    for arch, min_req in iter(min_req_memory.items()):
        if architecture.matches_architecture(arch):
            is_ok = mem_info.mem_total >= min_req
            msg = {} if is_ok else {'detected': mem_info.mem_total,
                                    'minimal_req': min_req}

    return msg


def process():
    memoryinfo = next(api.consume(MemoryInfo), None)
    if memoryinfo is None:
        raise StopActorExecutionError(message=("Missing information about Memory."))

    minimum_req_error = _check_memory(memoryinfo)

    if minimum_req_error:
        title = 'Minimum memory requirements for RHEL 8 are not met'
        summary = 'Memory detected: {} KiB, required: {} KiB'.format(minimum_req_error['detected'],
                                                                     minimum_req_error['minimal_req'])
        reporting.create_report([
                          reporting.Title(title),
                          reporting.Summary(summary),
                          reporting.Severity(reporting.Severity.HIGH),
                          reporting.Groups([reporting.Groups.SANITY, reporting.Groups.INHIBITOR]),
                      ])
