from leapp.actors import Actor
from leapp.tags import IPUWorkflowTag, ExperimentalTag, PreparationPhaseTag
from leapp.libraries.actor.yumupgradability import secure_yum_upgradability


class YumUpgradability(Actor):
    """
    Copy yum v3 configuration to yum v4 /etc/dnf directory

    Steps
        1) Create /etc/dnf directory
        2) Copy yum configuration to the /etc/dnf directory
        3) Make symlinks under /etc/yum
    """

    name = 'yum_upgradability'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        """
        Process yum upgradability actor
        """
        secure_yum_upgradability()
