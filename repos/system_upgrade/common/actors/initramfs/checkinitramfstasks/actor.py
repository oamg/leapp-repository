from leapp.actors import Actor
from leapp.libraries.actor import checkinitramfstasks
from leapp.models import Report, TargetInitramfsTasks, UpgradeInitramfsTasks
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class CheckInitramfsTasks(Actor):
    """
    Inhibit the upgrade if conflicting "initramfs" tasks are detected

    It's possible that some actors could provide conflicting requests
    (e.g. install system dracut module A & custom (from own path) dracut
    module A). This actor prevents system from upgrading if conflicting tasks
    for the upgrade or target initramfses are detected.
    """

    name = 'check_initramfs_tasks'
    consumes = (UpgradeInitramfsTasks, TargetInitramfsTasks)
    produces = (Report,)
    tags = (TargetTransactionChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkinitramfstasks.process()
