from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RegisterRubyIRBAdjustment(Actor):
    """
    Registers a workaround which will adjust the Ruby IRB directories during the upgrade.
    """

    name = 'register_ruby_irb_adjustment'
    consumes = ()
    produces = (DNFWorkaround,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        self.produce(
            DNFWorkaround(
                display_name='IRB directory fix',
                script_path=self.get_tool_path('handlerubyirbsymlink'),
            )
        )
