from leapp.actors import Actor
from leapp.libraries.common.reporting import report_with_remediation
from leapp.models import ActiveKernelModulesFacts, WhitelistedKernelModules
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKernelModules(Actor):
    """
    Actor checks if any loaded RHEL 7 kernel module is missing in the RHEL 8.
    If yes, the upgrade process will be inhibited.

    Inhibition is done because missing kernel module on the RHEL 8 system may
    mean that the hardware using such module as a driver would not work on the
    RHEL 8.

    Note:
     - List of kernel modules missing on the RHEL 8 system is located in the
        files/removed_modules.txt file.
    """
    name = "check_kernel_modules"
    consumes = (ActiveKernelModulesFacts, WhitelistedKernelModules)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        with open("files/removed_modules.txt", "r") as removed:
            removed_modules = [x.strip() for x in removed.readlines()]
            whitelisted_modules = set()
            modules_to_report = set()

            for fact in self.consume(WhitelistedKernelModules):
                whitelisted_modules.update(fact.whitelisted_modules)

            for fact in self.consume(ActiveKernelModulesFacts):
                for active_module in fact.kernel_modules:
                    if active_module.filename in whitelisted_modules:
                        continue
                    if active_module.filename in removed_modules:
                        modules_to_report.add(active_module.filename)

            if modules_to_report:
                title = 'Detected unavailable kernel modules. Upgrade cannot proceed.'
                summary = ('The following kernel modules are not available on '
                           'the RHEL 8 system: \n     - {}'.format('\n     - '.join(modules_to_report)))
                remediation = ('Disable detected unavailable kernel modules in '
                               'order to proceed with the upgrade process.')
                report_with_remediation(title=title,
                                        summary=summary,
                                        remediation=remediation,
                                        severity='high',
                                        flags=['inhibitor'])
