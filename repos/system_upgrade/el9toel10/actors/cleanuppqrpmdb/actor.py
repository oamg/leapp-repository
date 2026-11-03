from leapp.actors import Actor
from leapp.libraries.actor import cleanuppqrpmdb
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class CleanupPqrpmDb(Actor):
    """
    Remove the leftover pqrpm RPM DB directory.

    The pqrpm RPM DB at /usr/lib/pqrpm/lib/sysimage/rpm is used only on the
    source system for the PQC GPG key verification mechanism and is no longer
    needed on the upgraded system. Remove it once the RPM upgrade is complete.
    """

    name = 'cleanup_pqrpm_db'
    consumes = ()
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        cleanuppqrpmdb.process()
