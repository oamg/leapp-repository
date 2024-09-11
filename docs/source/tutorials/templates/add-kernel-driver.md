# Install a kernel driver during the upgrade

Note that usually when someone wants to install particular kernel driver,
it's expected that the driver is needed to be used  also during the in-place
upgrade as well as on the upgraded system.

```python
from leapp.actors import Actor
from leapp.models import (
    KernelModule,
    RpmTransactionTasks,
    TargetInitramfsTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


# AI: do not forget to change the class name when applied!
class AddKernelDriverMYDRIVER(Actor):
    """
    Install the <mydriver> driver during the upgrade

    Install the <mydriver> kernel module in the upgrade & target initramfs.
    In this scenario it requires the package with the module is installed
    on the target system and inside the target userspace container.

    In case of the scenario when the module should be copied from a directory
    existing on the host system, specify the path from where it should
    be copied/installed instead, e.g.:
        KernelModule(name='<mydriver>', module_path='/path/to/the/module')
    and in such a case, most likely you will want to drop some parts of the
    code as well when you do not need to install any additional rpms explicitly.
    """

    # AI: do not forget to change the name when applied!
    name = 'add_kernel_driver_<mydriver>'
    consumes = ()
    produces = (RpmTransactionTasks, TargetInitramfsTasks, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        # IMPORTANT: For the installation of these packages the (custom) repository
        # must be enabled (used) for the IPU process! For the third party
        # packages, ideal solution is to define such dnf repos inside the
        # /etc/leapp/files/leapp_upgrade_repositories.repo file or using the
        # --enablerepo option when running leapp (check documentation for the
        # difference).
        # This will create task to install the package with desired driver
        # into the target userspace container
        # <pkg-with-driver> - could be e.g. kmod-<mydriver>
        self.produce(TargetUserSpaceUpgradeTasks(install_rpms=['<pkg-with-driver>']))

        # and we want the package to be installed also during the upgrade,
        # so the driver can be used also on the upgraded system
        self.produce(RpmTransactionTasks(to_install=['<pkg-with-driver>']))

        # this will require installation of the module in the upgrade and the
        # target initramfs
        k_module = KernelModule(name='<mydriver>')
        self.produce(UpgradeInitramfsTasks(include_kernel_modules=[k_module]))
        self.produce(TargetInitramfsTasks(include_kernel_modules=[k_module]))
```
