from leapp.actors import Actor
from leapp.models import WhitelistedKernelModules
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class WhitelistKernelModules(Actor):
    """
    Actor produces message that contains list of kernel modules that are
    present on the RHEL7 system but missing on the RHEL8. However, these
    specific modules are considered whitelisted and CheckKernelModules
    actor will take this into account and will not inhibit upgrade
    in case any of the whitelisted modules are loaded.
    """
    name = "whitelist_kernel_modules"
    consumes = ()
    produces = (WhitelistedKernelModules,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        # These modules are present on the clean RHEL7.6 installation
        # in virtual machine via vagrant. They are whitelisted because
        # we do not want to inhibit upgrade from clean installation.
        whitelisted_modules = [
            'ablk_helper', 'crct10dif_common', 'cryptd', 'floppy',
            'gf128mul', 'glue_helper', 'iosf_mbi', 'pata_acpi', 'virtio',
            'virtio_pci', 'virtio_ring'
        ]
        self.produce(WhitelistedKernelModules(whitelisted_modules=whitelisted_modules))
