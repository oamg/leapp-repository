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

    Note:
     - List of kernel modules missing on the RHEL 8 system is located in the
        files/removed_modules.txt file.
     - Whitelisted modules located in the files/whitelisted_modules.txt are not
        going to inhibit upgrade.

    FIXME:
     - Currently, we have whitelisted every module from files/removed_modules.txt.
        This has been done due to the fact that we need to investigate in depth
        what each module does and if it is safe to add/remove it to/from the
        whitelist.
    """
    name = "check_kernel_modules"
    consumes = (ActiveKernelModulesFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag,)

    def process(self):
        with open("files/removed_modules.txt", "r") as removed, \
            open("files/whitelisted_modules.txt", "r") as whitelisted:
            removed_modules = [x.strip() for x in removed.readlines()]
            whitelisted_modules = [x.strip() for x in whitelisted.readlines()]

            modules_to_report = set()
            for fact in self.consume(ActiveKernelModulesFacts):
                for active_module in fact.kernel_modules:
                    if active_module.filename in removed_modules \
                        and active_module.filename not in whitelisted_modules:
                        modules_to_report.add(active_module.filename)

            if modules_to_report:
                title = "Detected unavailable kernel modules. Upgrade can't proceed."
                summary = "The following kernel modules are not available on" \
                          " the RHEL 8 system: {}".format(modules_to_report)
                remediation = "Disable detected unavailable kernel modules in" \
                              " order to proceed with the upgrade process."
                report_with_remediation(title=title,
                                        summary=summary,
                                        remediation=remediation,
                                        severity='high',
                                        flags=['inhibitor'])
