
from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

SUPPORTED_MACHINE_TYPES = [2964, 2965, 3906, 3907]


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return
    cpuinfo = next(api.consume(CPUInfo), None)
    if cpuinfo is None:
        raise StopActorExecutionError(message=("Missing information about CPU."))

    if not cpuinfo.machine_type:
        # this is not expected to happen, but in case...
        api.curernt_logger().warning("The machine (CPU) type is empty.")

    if cpuinfo.machine_type not in SUPPORTED_MACHINE_TYPES:
        summary = ("The system is not possible to upgrade because of unsupported"
                   " type of the processor. Based on the official documentation,"
                   " z13 and z14 processors are supported on the Red Hat Enterprise"
                   " Linux 8 system for the IBM Z architecture. The supported processors"
                   " have machine types {}. The detected machine type of the CPU is '{}'."
                   .format(", ".join([str(i) for i in SUPPORTED_MACHINE_TYPES]), cpuinfo.machine_type))
        report = [
            reporting.Title("The processor is not supported by the target system."),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SANITY]),
            reporting.Flags([reporting.Flags.INHIBITOR]),
            reporting.ExternalLink(
                title="Considerations in adopting RHEL 8",
                url=("https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/"
                     "html-single/considerations_in_adopting_rhel_8/"
                     "index#changes-in-gcc-in-rhel-8_changes-in-toolchain-since-rhel-7"))
        ]
        reporting.create_report(report)
