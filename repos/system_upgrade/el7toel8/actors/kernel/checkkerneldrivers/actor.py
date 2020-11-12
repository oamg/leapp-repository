from leapp.actors import Actor
from leapp.libraries.actor.checkkerneldrivers import (
    check_drivers,
    get_present_drivers,
    get_removed_drivers,
)
from leapp.models import PCIDevices
from leapp.reporting import Report, create_report
from leapp import reporting
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKernelDrivers(Actor):
    """
    Actor checks if any loaded RHEL7 kernel driver is missing in the RHEL8.
    If yes, the upgrade process will be inhibited.

    Inhibition is done because missing kernel driver on the RHEL8 system may
    mean that the hardware using such driver would not work on the RHEL8.

    Note:
     - List of kernel drivers missing on the RHEL8 system is located in the
        files/removed_drivers.txt file.
    """
    name = 'check_kernel_drivers'
    consumes = (PCIDevices,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        removed_file = 'files/removed_drivers.txt'
        conflicting = check_drivers(get_removed_drivers(removed_file), get_present_drivers())

        if conflicting:
            title = ('Detected loaded kernel drivers which have been removed '
                     'in RHEL 8. Upgrade cannot proceed.')
            URL = ('https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html-single/'
                   'considerations_in_adopting_rhel_8/index#removed-device-drivers_hardware-enablement')
            summary = ('Support for the following RHEL 7 '
                       'device drivers has been removed in RHEL 8: \n     - {}'
                       '\nPlease see {} for details.'.format('\n     - '.join(conflicting), URL))
            remediation = ('Please disable detected kernel drivers in '
                           'order to proceed with the upgrade process using the rmmod or modprobe -r.')
            create_report([
                reporting.Title(title),
                reporting.Summary(summary),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.KERNEL, reporting.Groups.DRIVERS, reporting.Groups.INHIBITOR]),
                reporting.Remediation(hint=remediation)
            ] + [reporting.RelatedResource('kernel-driver', kd) for kd in conflicting])
