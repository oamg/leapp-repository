from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RegisterYumAdjustment(Actor):
    """
    Registers a workaround which will adjust the yum directories during the upgrade.
    """

    name = 'register_yum_adjustment'
    consumes = ()
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(
            DNFWorkaround(
                display_name='yum config fix',
                script_path=self.get_tool_path('handleyumconfig'),
            )
        )
