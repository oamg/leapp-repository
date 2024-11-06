from leapp.actors import Actor
from leapp.models import DNFWorkaround
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RegisterRubyIRBAdjustment(Actor):
    """
    Register a workaround to allow rubygem-irb's directory -> symlink conversion.

    The /usr/share/ruby/irb has been moved from a directory to a symlink
    in RHEL 9 and this conversion was not handled on RPM level.
    This leads to DNF reporting package file conflicts when a major upgrade
    is attempted and rubygem-irb (or ruby-irb) is installed.

    Register "handlerubyirbsymlink" script that removes the directory prior
    to DNF upgrade and allows it to create the expected symlink in place of
    the removed directory.
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
