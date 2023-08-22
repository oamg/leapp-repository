from leapp.actors import Actor
from leapp.libraries.actor.checkdynamiclinkerconfiguration import check_dynamic_linker_configuration
from leapp.models import DynamicLinkerConfiguration, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckDynamicLinkerConfiguration(Actor):
    """
    Check for customization of dynamic linker configuration.

    The in-place upgrade could potentionally be impacted in a negative way due
    to the customization of dynamic linker configuration by user. This actor creates high
    severity report upon detecting such customization.
    """

    name = 'check_dynamic_linker_configuration'
    consumes = (DynamicLinkerConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        check_dynamic_linker_configuration()
