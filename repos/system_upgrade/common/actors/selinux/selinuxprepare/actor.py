from leapp.actors import Actor
from leapp.libraries.actor import selinuxprepare
from leapp.models import SELinuxCustom, SELinuxModules
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class SELinuxPrepare(Actor):
    """
    Remove selinux policy customizations before updating selinux-policy* packages

    Policy customizations in the original system could cause policy package
    upgrade to fail and therefore need to be removed.
    Customizations introduced by semanage are removed first, followed by custom
    policy modules gathered by SELinuxContentScanner.
    """

    name = 'selinuxprepare'
    consumes = (SELinuxCustom, SELinuxModules)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        selinuxprepare.remove_semanage_customizations()
        selinuxprepare.remove_custom_modules()
