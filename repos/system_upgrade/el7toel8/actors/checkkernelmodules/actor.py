from leapp.actors import Actor
from leapp.models import ActiveKernelModulesFacts
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKernelModules(Actor):
    """
    Actor checks if any loaded RHEL 7 kernel module is missing in the RHEL 8.
    If yes, the upgrade process will be inhibited.

    Inhibition is done because missing kernel module on the RHEL 8 system may
    mean that the hardware using such module as a driver would not work on the
    RHEL 8.
    """
    name = "check_kernel_modules"
    consumes = (ActiveKernelModulesFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        with open("files/removed_modules.txt", "r") as file_handler:
            removed_modules = [x.strip() for x in file_handler.readlines()]
            modules_to_report = []
            for fact in self.consume(ActiveKernelModulesFacts):
                for active_module in fact.kernel_modules:
                    if active_module.filename in removed_modules:
                        modules_to_report.append(active_module.filename)

            if modules_to_report:
                title = "Detected unavailable kernel modules. Upgrade can't proceed"
                summary = "The following kernel modules are not available on" \
                          " the RHEL 8 system: {}".format(modules_to_report)
                remediation = "Disable detected unavailable kernel modules in" \
                              " order to proceed with the upgrade process."
                report_with_remediation(title=title,
                                        summary=summary,
                                        remediation=remediation,
                                        severity='high',
                                        flags=['inhibitor'])
