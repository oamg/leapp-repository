from leapp.actors import Actor
from leapp.libraries.actor import scanpamuserdb
from leapp.models import PamUserDbLocation
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanPamUserDb(Actor):
    """
    Scan the PAM service folder for the location of pam_userdb databases
    """

    name = 'scan_pam_user_db'
    consumes = ()
    produces = (PamUserDbLocation,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(scanpamuserdb.parse_pam_config_folder('/etc/pam.d/'))
