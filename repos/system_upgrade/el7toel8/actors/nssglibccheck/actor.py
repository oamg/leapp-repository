import os

from leapp.actors import Actor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp import reporting
from leapp.libraries.actor import nssglibccheck

# Path to NSS configuration file
NSS_CONFIG_PATH = '/etc/nsswitch.conf'

# List of affected modules
BLACKLIST = ('wins', 'winbind',)


class NSSGlibcCheckActor(Actor):
    produces = (reporting.Report,)
    consumes = ()
    name = 'nss_glibc_check_actor'
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        if not os.path.exists(NSS_CONFIG_PATH):
            return

        with open(NSS_CONFIG_PATH, 'r') as fp:
            stripped = [line.strip() for line in fp.readlines()]
            nssglibccheck.process_lines(stripped, BLACKLIST, NSS_CONFIG_PATH)
