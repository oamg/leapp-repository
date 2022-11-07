import os

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import CopyFile, TargetUserSpaceUpgradeTasks, UpgradeInitramfsTasks

ZFCP_CONF = '/etc/zfcp.conf'


def process():
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        return
    copy_files = []
    if os.path.isfile(ZFCP_CONF):
        # the file has to be copied into the targetuserspace container first,
        # then it can be included into the initramfs ==> both messages are
        # needed to be produced
        copy_files = [CopyFile(src=ZFCP_CONF)]
        api.produce(UpgradeInitramfsTasks(include_files=[ZFCP_CONF]))
    else:
        api.current_logger().info(
            "The {} file has not been discovered. ZFCP not used."
            .format(ZFCP_CONF)
        )
    api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files, install_rpms=['s390utils-core']))
