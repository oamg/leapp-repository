from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import architecture, version
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdline, RoceDetected

FMT_LIST_SEPARATOR = '\n    - {}'
DOC_URL = 'https://red.ht/predictable-network-interface-device-names-on-the-system-z-platform'


def is_kernel_arg_set():
    """
    Return True if the system is booted with net.naming-scheme=rhel-8.7

    Important: it's really expected the argument is rhel-8.7 always.
    So not rhel-8.8, rhel-9.0, ... etc.
    """
    kernel_args = next(api.consume(KernelCmdline), None)
    if not kernel_args:
        # This is theoretical. If this happens, something is terribly wrong
        # already - so raising the hard error.
        raise StopActorExecutionError('Missing the KernelCmdline message!')
    for param in kernel_args.parameters:
        if param.key != 'net.naming-scheme':
            continue
        if param.value == 'rhel-8.7':
            return True
        api.current_logger().warning(
            'Detected net.naming-scheme with unexpected value: {}'
            .format(param.value)
        )
        return False
    return False


def _fmt_list(items):
    return ''.join([FMT_LIST_SEPARATOR.format(i) for i in items])


def _report_old_version(roce):
    roce_nics = roce.roce_nics_connected + roce.roce_nics_connecting
    reporting.create_report([
        reporting.Title('A newer version of RHEL 8 is required for the upgrade with RoCE.'),
        reporting.Summary(
            'The RHEL 9 system uses different network schemes for NIC names'
            ' than RHEL 8.'
            ' RHEL {version} does not provide functionality to be able'
            ' to set the system configuration in a way the network interface'
            ' names used by RoCE are persistent on both (RHEL 8 and RHEL 9)'
            ' systems.'
            ' The in-place upgrade from the current version of RHEL to RHEL 9'
            ' will break the RoCE network configuration.'
            '\n\nRoCE detected on following NICs:{nics}'
            .format(
                version=version.get_source_version(),
                nics=_fmt_list(roce_nics)
            )
        ),
        reporting.Remediation(hint=(
            'Update the system to RHEL 8.8 or newer using DNF and then reboot'
            ' the system prior the in-place upgrade to RHEL 9.'
        )),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([
            reporting.Groups.INHIBITOR,
            reporting.Groups.ACCESSIBILITY,
            reporting.Groups.SANITY,
        ]),
    ])


def _report_wrong_setup(roce):
    roce_nics = roce.roce_nics_connected + roce.roce_nics_connecting
    reporting.create_report([
        reporting.Title('Invalid RoCE configuration for the in-place upgrade'),
        reporting.Summary(
            'The RHEL 9 system uses different network schemes for NIC names'
            ' than RHEL 8.'
            ' The below listed RoCE NICs need to be reconfigured to the new'
            ' interface naming scheme in order to prevent loss of network'
            ' access to your system via these interfaces after the upgrade.'
            ' For more information, see: {url}'
            '\n\nRoCE detected on the following NICs:{nics}'
            .format(nics=_fmt_list(roce_nics), url=DOC_URL)
        ),
        reporting.Remediation(hint=(
            'Prerequisite for upgrading to RHEL9.x:'
            'In RHEL 8, all RoCE cards must be configured with the interface'
            ' names they should have in RHEL9.x.\n'
            'For more information, see chapter 1.4 of the RHEL8 Product'
            ' Documentation (see the attached link) and follow these steps:\n'
            '1.) determine the current interface device names of the RoCE'
            ' cards that are in "connected to" or in "connecting" state\n'
            '2.) determine if UID uniqueness is set for these cards\n'
            '3.) compute new interface device names from the UID or the'
            ' function ID, respectively\n'
            '4.) change the network interface device names in ifcfg'
            ' files\n'
            '5.) set the kernel parameter net.naming-scheme=rhel-8.7 in the'
            ' effective .conf file in /boot/loader/entries\n'
            '6.) adjust other settings that rely on the interface device names'
            ' (e.g. firewall) by changing the interface device names'
            ' accordingly\n'
            '7.) run `zipl -V` and reboot the system\n'
            '8.) check your network connectivity\n'
            '\n'
            'Caution: Creating an incorrect configuration might cause the loss'
            ' of your network connection after reboot!'
        )),
        reporting.ExternalLink(
            title='Predictable network interface device names on the System z platform',
            url=DOC_URL),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([
            reporting.Groups.INHIBITOR,
            reporting.Groups.ACCESSIBILITY,
            reporting.Groups.SANITY,
        ]),
    ])


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        # The check is valid only on S390X architecture
        return
    roce = next(api.consume(RoceDetected), None)
    if not roce or not (roce.roce_nics_connected or roce.roce_nics_connecting):
        # No used RoCE detected - nothing to do
        api.current_logger().debug('Skipping RoCE checks: No RoCE card detected.')
        return
    if version.matches_source_version('<= 8.6'):
        _report_old_version(roce)
    if not is_kernel_arg_set():
        _report_wrong_setup(roce)
