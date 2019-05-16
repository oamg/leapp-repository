from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxModule, SELinuxCustom, SELinuxFacts, SELinuxRequestRPMs, RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.libraries.actor import library


WORKING_DIRECTORY = '/tmp/selinux/'

class SELinuxContentScanner(Actor):
    '''
    Scan the system for any SELinux customizations

    Find SELinux policy customizations (custom policy modules and changes
    introduced by semanage) and save them in SELinuxModules and SELinuxCustom
    models. Customizations that are incompatible with SELinux policy on RHEL-8
    are removed.
    '''
    name = 'selinuxcontentscanner'
    consumes = (SELinuxFacts,)
    produces = (SELinuxModules, SELinuxCustom, SELinuxRequestRPMs, RpmTransactionTasks)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        # exit if SELinux is disabled
        for fact in self.consume(SELinuxFacts):
            if not fact.enabled:
                return

        (semodule_list, rpms_to_keep, rpms_to_install) = library.getSELinuxModules()

        self.produce(SELinuxModules(modules=semodule_list))
        self.produce(
            RpmTransactionTasks(
                to_install = rpms_to_install,
                # possibly not necessary - dnf should not remove RPMs (that exist in both RHEL 7 and 8) durign update
                to_keep = rpms_to_keep
            )
        )
        # this is produced so that we can later verify that the RPMs are present after upgrade
        self.produce(
            SELinuxRequestRPMs(
                to_install = rpms_to_install,
                to_keep = rpms_to_keep
            )
        )

        (semanage_valid, semanage_removed) = library.getSELinuxCustomizations()

        self.produce(
            SELinuxCustom(
                commands=semanage_valid,
                removed=semanage_removed
            )
        )