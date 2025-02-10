from collections import namedtuple

from leapp import reporting
from leapp.libraries.common.config.architecture import ARCH_X86_64, matches_architecture
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import CPUInfo

X86_64_BASELINE_FLAGS = ['cmov', 'cx8', 'fpu', 'fxsr', 'mmx', 'syscall', 'sse', 'sse2']
X86_64_V2_FLAGS = ['cx16', 'lahf_lm', 'popcnt', 'pni', 'sse4_1', 'sse4_2', 'ssse3']
X86_64_V3_FLAGS = ['avx2', 'bmi1', 'bmi2', 'f16c', 'fma', 'abm', 'movbe', 'xsave']

MicroarchInfo = namedtuple('MicroarchInfo', ('required_flags', 'extra_report_fields', 'microarch_ver'))


def _inhibit_upgrade(missing_flags, target_rhel, microarch_ver, extra_report_fields=None):
    title = 'Current x86-64 microarchitecture is unsupported in {0}'.format(target_rhel)
    summary = ('{0} has a higher CPU requirement than older versions, it now requires a CPU '
               'compatible with {1} instruction set or higher.\n\n'
               'Missings flags detected are: {2}\n').format(target_rhel, microarch_ver, ', '.join(missing_flags))

    report_fields = [
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.SANITY]),
        reporting.Remediation(hint=('If a case of using virtualization, virtualization platforms often allow '
                                    'configuring a minimum denominator CPU model for compatibility when migrating '
                                    'between different CPU models. Ensure that minimum requirements are not below '
                                    'that of {0}\n').format(target_rhel)),
    ]

    if extra_report_fields:
        report_fields += extra_report_fields

    reporting.create_report(report_fields)


def process():
    """
    Check whether the processor matches the required microarchitecture.
    """

    if not matches_architecture(ARCH_X86_64):
        api.current_logger().info('Architecture not x86-64. Skipping microarchitecture test.')
        return

    cpuinfo = next(api.consume(CPUInfo))

    rhel9_microarch_article = reporting.ExternalLink(
        title='Building Red Hat Enterprise Linux 9 for the x86-64-v2 microarchitecture level',
        url='https://red.ht/rhel-9-intel-microarchitectures'
    )

    rhel10_microarch_article = reporting.ExternalLink(
        title='Building Red Hat Enterprise Linux 10 for the x86-64-v3 microarchitecture level',
        url='https://red.ht/rhel-10-intel-microarchitectures'
    )

    rhel_major_to_microarch_reqs = {
        '9': MicroarchInfo(microarch_ver='x86-64-v2',
                           required_flags=(X86_64_BASELINE_FLAGS + X86_64_V2_FLAGS),
                           extra_report_fields=[rhel9_microarch_article]),
        '10': MicroarchInfo(microarch_ver='x86-64-v3',
                            required_flags=(X86_64_BASELINE_FLAGS + X86_64_V2_FLAGS + X86_64_V3_FLAGS),
                            extra_report_fields=[rhel10_microarch_article]),
    }

    microarch_info = rhel_major_to_microarch_reqs.get(get_target_major_version())
    if not microarch_info:
        api.current_logger().info('No known microarchitecture requirements are known for target RHEL%s.',
                                  get_target_major_version())
        return

    missing_flags = [flag for flag in microarch_info.required_flags if flag not in cpuinfo.flags]
    api.current_logger().debug('Required flags missing: %s', missing_flags)
    if missing_flags:
        _inhibit_upgrade(missing_flags,
                         'RHEL{0}'.format(get_target_major_version()),
                         microarch_info.microarch_ver,
                         extra_report_fields=microarch_info.extra_report_fields)
