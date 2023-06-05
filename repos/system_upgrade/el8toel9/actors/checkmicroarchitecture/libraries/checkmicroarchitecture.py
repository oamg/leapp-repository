from leapp import reporting
from leapp.libraries.common.config.architecture import ARCH_X86_64, matches_architecture
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

X86_64_BASELINE_FLAGS = ['cmov', 'cx8', 'fpu', 'fxsr', 'mmx', 'syscall', 'sse', 'sse2']
X86_64_V2_FLAGS = ['cx16', 'lahf_lm', 'popcnt', 'pni', 'sse4_1', 'sse4_2', 'ssse3']


def _inhibit_upgrade(missing_flags):
    title = 'Current x86-64 microarchitecture is unsupported in RHEL9'
    summary = ('RHEL9 has a higher CPU requirement than older versions, it now requires a CPU '
               'compatible with x86-64-v2 instruction set or higher.\n\n'
               'Missings flags detected are: {}\n'.format(', '.join(missing_flags)))

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.ExternalLink(title='Building Red Hat Enterprise Linux 9 for the x86-64-v2 microarchitecture level',
                               url='https://red.ht/rhel-9-intel-microarchitectures'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.SANITY]),
        reporting.Remediation(hint=('If case of using virtualization, virtualization platforms often allow '
                                    'configuring a minimum denominator CPU model for compatibility when migrating '
                                    'between different CPU models. Ensure that minimum requirements are not below '
                                    'that of RHEL9\n')),
    ])


def process():
    """
    Check whether the processor matches the required microarchitecture.
    """

    if not matches_architecture(ARCH_X86_64):
        api.current_logger().info('Architecture not x86-64. Skipping microarchitecture test.')
        return

    cpuinfo = next(api.consume(CPUInfo))

    required_flags = X86_64_BASELINE_FLAGS + X86_64_V2_FLAGS
    missing_flags = [flag for flag in required_flags if flag not in cpuinfo.flags]
    api.current_logger().debug('Required flags missing: %s', missing_flags)
    if missing_flags:
        _inhibit_upgrade(missing_flags)
