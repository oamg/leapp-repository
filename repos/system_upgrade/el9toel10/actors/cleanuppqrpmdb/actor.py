from leapp.actors import Actor
from leapp.libraries.actor import cleanuppqrpmdb
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class CleanupPqrpm(Actor):
    """
    Remove the leftover pqrpm RPM DB directory.

    The pqrpm RPM DB at /usr/lib/pqrpm/lib/sysimage/rpm is used only on the
    source system for the PQC GPG key verification mechanism and is no longer
    needed on the upgraded system. It's the only file (directory) left after
    uninstallation of the package, so the entire /usr/lib/pqrpm is removed
    instead. Remove it once the RPM upgrade is complete.
    """

    name = 'cleanup_pqrpm'
    consumes = ()
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        cleanuppqrpmdb.process()
