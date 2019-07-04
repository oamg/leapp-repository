from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxCustom
from leapp.tags import PreparationPhaseTag, IPUWorkflowTag
from leapp.libraries.actor import library


class SELinuxPrepare(Actor):
    '''
    Remove selinux policy customizations before updating selinux-policy* packages

    RHEL-7 policy customizations could cause policy package upgrade to fail and therefore
    need to be removed. Customizations introduced by semanage are removed first,
    followed by custom policy modules gathered by SELinuxContentScanner.
    '''

    name = 'selinuxprepare'
    consumes = (SELinuxCustom, SELinuxModules)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        library.removeSemanageCustomizations()
        library.removeCustomModules()
