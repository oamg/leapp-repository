from leapp.actors import Actor
from leapp.models import (FilteredRpmTransactionTasks,
                          InstalledRedHatSignedRPM, PESRpmTransactionTasks,
                          RpmTransactionTasks)
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class FilterRpmTransactionTasks(Actor):
    """
    Filter RPM transaction events based on installed RPM packages

    In order to calculate a working DNF Upgrade transaction, Leapp can collect data from multiple
    sources and find workarounds for possible problems. This actor will filter all collected
    workarounds and keep only those relevants to current system based on installed packages.
    """

    name = 'check_rpm_transaction_events'
    consumes = (PESRpmTransactionTasks, RpmTransactionTasks, InstalledRedHatSignedRPM,)
    produces = (FilteredRpmTransactionTasks,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        installed_pkgs = set()
        for rpm_pkgs in self.consume(InstalledRedHatSignedRPM):
            installed_pkgs.update([pkg.name for pkg in rpm_pkgs.items])

        local_rpms = set()
        to_install = set()
        to_remove = set()
        to_keep = set()
        to_upgrade = set()
        for event in self.consume(RpmTransactionTasks, PESRpmTransactionTasks):
            local_rpms.update(event.local_rpms)
            to_install.update(event.to_install)
            to_remove.update(installed_pkgs.intersection(event.to_remove))
            to_keep.update(installed_pkgs.intersection(event.to_keep))

        to_remove.difference_update(to_keep)

        # run upgrade for the rest of RH signed pkgs which we do not have rule for
        to_upgrade = installed_pkgs - (to_install | to_remove)

        self.produce(FilteredRpmTransactionTasks(
            local_rpms=list(local_rpms),
            to_install=list(to_install),
            to_remove=list(to_remove),
            to_keep=list(to_keep),
            to_upgrade=list(to_upgrade)))
