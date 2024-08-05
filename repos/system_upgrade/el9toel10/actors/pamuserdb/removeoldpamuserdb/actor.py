from leapp.actors import Actor
from leapp.libraries.actor import removeoldpamuserdb
from leapp.models import PamUserDbLocation
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class RemoveOldPamUserDb(Actor):
    """
    Remove old pam_userdb databases
    """

    name = 'remove_old_pam_user_db'
    consumes = (PamUserDbLocation,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        removeoldpamuserdb.process()
