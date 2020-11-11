from leapp.actors import Actor
from leapp.libraries.actor import cupscheck
from leapp.models import CupsChangedFeatures, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CupsCheck(Actor):
    """
    Reports changes in configuration between CUPS 1.6.3 and 2.2.6

    Reports if user configuration contains features (interface scripts),
    directives (Include, PrintcapFormat, PassEnv, SetEnv,
    ServerCertificate, ServerKey) or directive values (Digest,
    BasicDigest). Some of them were removed for security reasons
    (interface scripts and directive Include), moved
    to cups-files.conf for security reasons (PassEnv, SetEnv).
    Others were removed (ServerCertificate, ServerKey, Digest,
    BasicDigest) or moved (PrintcapFormat) due deprecation.
    """

    name = 'cups_check'
    consumes = (CupsChangedFeatures,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        cupscheck.make_reports()
