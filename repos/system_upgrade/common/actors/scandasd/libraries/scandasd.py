import os

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks

DASD_CONF = '/etc/dasd.conf'


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return
    copy_files = []
    if os.path.isfile(DASD_CONF):
        # the file has to be copied into the targetuserspace container first,
        # then it can be included into the initramfs ==> both messages are
        # needed to be produced
        copy_files = [CopyFile(src=DASD_CONF)]
        api.produce(UpgradeInitramfsTasks(include_files=[DASD_CONF]))
    else:
        api.current_logger().warning(
            "The {} file has not been discovered. DASD not used?"
            .format(DASD_CONF)
        )
    api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files, install_rpms=['s390utils-core']))
