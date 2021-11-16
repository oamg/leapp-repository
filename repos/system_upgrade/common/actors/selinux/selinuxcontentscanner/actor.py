from leapp.actors import Actor
from leapp.libraries.actor import selinuxcontentscanner
from leapp.models import RpmTransactionTasks, SELinuxCustom, SELinuxFacts, SELinuxModules, SELinuxRequestRPMs
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SELinuxContentScanner(Actor):
    """
    Scan the system for any SELinux customizations

    Find SELinux policy customizations (custom policy modules and changes
    introduced by semanage) and save them in SELinuxModules and SELinuxCustom
    models. Customizations that are incompatible with SELinux policy on RHEL-8
    are removed.
    """

    name = 'selinuxcontentscanner'
    consumes = (SELinuxFacts,)
    produces = (SELinuxModules, SELinuxCustom, SELinuxRequestRPMs, RpmTransactionTasks)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        # exit if SELinux is disabled
        for fact in self.consume(SELinuxFacts):
            if not fact.enabled:
                return

        (semodule_list, template_list, rpms_to_install,) = selinuxcontentscanner.get_selinux_modules()

        self.produce(
            SELinuxModules(
                modules=semodule_list,
                templates=template_list
            )
        )
        self.produce(
            RpmTransactionTasks(
                to_install=rpms_to_install
            )
        )
        # this is produced so that we can later verify that the RPMs are present after upgrade
        self.produce(
            SELinuxRequestRPMs(
                to_install=rpms_to_install
            )
        )

        (semanage_valid, semanage_removed,) = selinuxcontentscanner.get_selinux_customizations()

        self.produce(
            SELinuxCustom(
                commands=semanage_valid,
                removed=semanage_removed
            )
        )
