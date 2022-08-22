import os

from leapp.actors import Actor
from leapp.libraries.common.pam import PAM
from leapp.libraries.stdlib import api
from leapp.models import PamConfiguration, PamService
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PamModulesScanner(Actor):
    """
    Scan the pam directory for services and modules used in them

    This produces a PAMConfiguration message containing the whole
    list of configured PAM services and what modules they contain.
    """

    name = 'pam_modules_scanner'
    consumes = ()
    produces = (PamConfiguration, )
    tags = (FactsPhaseTag, IPUWorkflowTag, )

    def process(self):
        conf = []
        path = "/etc/pam.d/"
        for f in os.listdir(path):
            pam_file = os.path.join(path, f)
            # Ignore symlinks (usually handled by authconfig)
            if not os.path.isfile(pam_file) or os.path.islink(pam_file):
                continue

            # Use the existing PAM library to parse the files, but unpack it to our model
            try:
                content = PAM.read_file(pam_file)
                modules = PAM(content)
                service = PamService(service=f, modules=modules.modules)
                conf.append(service)
            except OSError as err:
                # if leapp can not read that file it will probably not be important
                api.current_logger().warning('Failed to read file {}: {}'.format(pam_file, err.strerror))

        pam = PamConfiguration(services=conf)
        self.produce(pam)
