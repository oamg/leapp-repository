from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RegisterRubyIRBAdjustment(Actor):
    """
    Register a workaround to allow rubygem-irb's symlink -> directory conversion.

    The /usr/share/ruby/irb has been moved from a symlink to a directory
    in RHEL 10 and this conversion was not handled on the RPM level.
    This leads to DNF reporting package file conflicts when a major upgrade
    is attempted and rubygem-irb is installed.

    Register "handlerubyirbsymlink" script that removes the symlink prior
    to DNF upgrade and allows it to create the expected directory in place of
    the removed symlink.
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
