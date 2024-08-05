from leapp.actors import Actor
from leapp.libraries.actor import convertpamuserdb
from leapp.models import PamUserDbLocation
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class ConvertPamUserDb(Actor):
    """
    Convert the pam_userdb databases to GDBM
    """

    name = 'convert_pam_user_db'
    consumes = (PamUserDbLocation,)
    produces = ()
    tags = (PreparationPhaseTag, IPUWorkflowTag)

    def process(self):
        convertpamuserdb.process()
