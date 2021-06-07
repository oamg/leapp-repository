from leapp.actors import Actor
from leapp.libraries.common.module import get_enabled_modules
from leapp.models import EnabledModules, Module
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class GetEnabledModules(Actor):
    """
    Provides data about which module streams are enabled on the source system.
    """

    name = 'get_enabled_modules'
    consumes = ()
    produces = (EnabledModules,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        modules = [Module(name=m.getName(), stream=m.getStream()) for m in get_enabled_modules()]
        self.produce(EnabledModules(modules=modules))
