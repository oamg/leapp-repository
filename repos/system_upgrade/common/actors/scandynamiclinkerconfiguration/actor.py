from leapp.actors import Actor
from leapp.libraries.actor.scandynamiclinkerconfiguration import scan_dynamic_linker_configuration
from leapp.models import DistributionSignedRPM, DynamicLinkerConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanDynamicLinkerConfiguration(Actor):
    """
    Scan the dynamic linker configuration and find modifications.

    The dynamic linker configuration files can be used to replace standard libraries
    with different custom libraries. The in-place upgrade does not support customization
    of this configuration by user. This actor produces information about detected
    modifications.
    """

    name = 'scan_dynamic_linker_configuration'
    consumes = (DistributionSignedRPM,)
    produces = (DynamicLinkerConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        scan_dynamic_linker_configuration()
