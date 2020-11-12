
from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

SUPPORTED_MACHINE_TYPES = [2964, 2965, 3906, 3907, 8561, 8562]


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return
    cpuinfo = next(api.consume(CPUInfo), None)
    if cpuinfo is None:
        raise StopActorExecutionError(message=("Missing information about CPU."))

    if not cpuinfo.machine_type:
        # this is not expected to happen, but in case...
        api.current_logger().warning("The machine (CPU) type is empty.")

    if cpuinfo.machine_type not in SUPPORTED_MACHINE_TYPES:
        summary = ("The system is not possible to upgrade because of unsupported"
                   " type of the processor. Based on the official documentation,"
                   " z13, z14 and z15 processors are supported on the Red Hat Enterprise"
                   " Linux 8 system for the IBM Z architecture. The supported processors"
                   " have machine types {}. The detected machine type of the CPU is '{}'."
                   .format(", ".join([str(i) for i in SUPPORTED_MACHINE_TYPES]), cpuinfo.machine_type))
        report = [
            reporting.Title("The processor is not supported by the target system."),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY, reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(
                title="Considerations in adopting RHEL 8",
                url=("https://access.redhat.com/ecosystem/hardware/#/search?p=1&"
                     "c_version=Red%20Hat%20Enterprise%20Linux%208&ch_architecture=s390x"))
        ]
        reporting.create_report(report)
