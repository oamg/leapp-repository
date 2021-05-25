from leapp.actors import Actor
from leapp.libraries.common.module import get_enabled_modules
from leapp.models import EnabledModule, EnabledModules
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class GetEnabledModules(Actor):
    """
    No documentation has been provided for the get_enabled_modules actor.
    """

    name = 'get_enabled_modules'
    consumes = ()
    produces = (EnabledModules,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        modules = [EnabledModule(name=m.getName(), stream=m.getStream()) for m in get_enabled_modules()]
        return EnabledModules(modules=modules)
