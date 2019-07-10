from leapp.actors import Actor
from leapp.libraries.common.reporting import report_with_remediation
from leapp.models import ActiveKernelModulesFacts, WhitelistedKernelModules, UdevAdmInfoData
from leapp.reporting import Report
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
     - Whitelisted modules that are not going to be reported are consumed from
        the WhitelistedKernelModules
    """
    name = 'check_kernel_drivers'
    consumes = (ActiveKernelModulesFacts, WhitelistedKernelModules, UdevAdmInfoData)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        with open('files/removed_drivers.txt', 'r') as removed:
            removed_drivers = []
            whitelisted_modules = set()
            collected_drivers = set()
            drivers_to_report = set()

            # Extracting kernel drivers from the files/removed_drivers.txt.
            for line in removed.readlines():
                token = line.strip()
                if token.startswith('#') or not token:
                    # We do not want comments or empty lines.
                    continue
                removed_drivers.append(token)

            # Consuming whitelisted kernel modules.
            for fact in self.consume(WhitelistedKernelModules):
                whitelisted_modules.update(fact.whitelisted_modules)

            # Collecting only non-whitelisted drivers that are part of the
            # files/removed_drivers.txt.
            for fact in self.consume(ActiveKernelModulesFacts):
                for active_module in fact.kernel_modules:
                    if active_module.filename in whitelisted_modules:
                        continue
                    if active_module.filename in removed_drivers:
                        collected_drivers.add(active_module.filename)

            # Going over the collected drivers and considering for reporting only
            # those drivers that are currently used by some device.
            udevadm_db = ''
            for fact in self.consume(UdevAdmInfoData):
                udevadm_db += fact.db
            for line in udevadm_db.split('\n'):
                if 'E: DRIVER=' in line:
                    _, driver = line.split('=')
                    if driver in collected_drivers:
                        drivers_to_report.add(driver)

            # In the end, we are only going to report drivers that are:
            # - removed in the RHEL8 (are part of files/removed_drivers.txt)
            # - not whitelisted
            # - currently being used by some device
            if drivers_to_report:
                title = ('Detected loaded kernel drivers which have been removed '
                         'in RHEL 8. Upgrade cannot proceed.')
                URL = ('https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html-single/'
                       'considerations_in_adopting_rhel_8/index#removed-device-drivers_hardware-enablement')
                summary = ('Support for the following currently loaded RHEL 7 '
                           'device drivers has been removed in RHEL 8: \n     - {}'
                           '\nPlease see {} for details.'.format('\n     - '.join(drivers_to_report), URL))
                remediation = ('Please disable detected kernel drivers in '
                               'order to proceed with the upgrade process using the rmmod tool.')
                report_with_remediation(title=title,
                                        summary=summary,
                                        remediation=remediation,
                                        severity='high',
                                        flags=['inhibitor'])
