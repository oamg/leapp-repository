import itertools
import sys

from leapp.cli.commands.config import get_config
from leapp.exceptions import UsageError
from leapp.messaging.answerstore import AnswerStore
from leapp.utils.clicmd import command, command_opt


@command('answer', help='Manage answerfile generation: register persistent user choices for specific dialog sections')
@command_opt('section', action='append', metavar='dialog_sections',
             help='Register answer for a specific section in the answerfile')
@command_opt('add', is_flag=True,
             help='If set sections will be created even if missing in original answerfile')
def answer(args):
    """A command to record user choices to the questions in the answerfile.
       Saves user answer between leapp preupgrade runs.
    """
    cfg = get_config()
    if args.section:
        args.section = list(itertools.chain(*[i.split(',') for i in args.section]))
    else:
        raise UsageError('At least one dialog section must be specified, ex. --section dialog.option=mychoice')
    try:
        sections = [tuple((dialog_option.split('.', 2) + [value]))
                    for dialog_option, value in [s.split('=', 2) for s in args.section]]
    except ValueError:
        raise UsageError("A bad formatted section has been passed. Expected format is dialog.option=mychoice")
    answerfile_path = cfg.get('report', 'answerfile')
    answerstore = AnswerStore()
    answerstore.load(answerfile_path)
    for dialog, option, value in sections:
        answerstore.answer(dialog, option, value)
    not_updated = answerstore.update(answerfile_path, allow_missing=args.add)
    if not_updated:
        sys.stderr.write("WARNING: Only sections found in original userfile can be updated, ignoring {}\n".format(
            ",".join(not_updated)))


def register(base_command):
    """
    Registers `leapp answer`
    """
    base_command.add_sub(answer)
