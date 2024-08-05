from leapp.actors import Actor
from leapp.libraries.actor import checkpamuserdb
from leapp.models import PamUserDbLocation, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPamUserDb(Actor):
    """
    Create report with the location of pam_userdb databases
    """

    name = 'check_pam_user_db'
    consumes = (PamUserDbLocation,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkpamuserdb.process()
