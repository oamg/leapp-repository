import os
import uuid
from argparse import Namespace

from leapp.cli.commands.upgrade import upgrade, util
from leapp.exceptions import CommandError
from leapp.utils.audit import Execution, get_connection
from leapp.utils.audit.contextclone import clone_context
from leapp.utils.clicmd import command, command_arg, command_opt

RERUN_SUPPORTED_PHASES = ('FirstBoot',)


@command('rerun', help='Re-runs the upgrade from the given phase and using the information and progress '
         'from the last invocation of leapp upgrade.')
@command_arg('from-phase',
             help='Phase to start running from again. Supported values: {}'.format(', '.join(RERUN_SUPPORTED_PHASES)))
@command_opt('only-actors-with-tag', action='append', metavar='TagName',
             help='Restrict actors to be re-run only with given tags. Others will not be executed')
@command_opt('debug', is_flag=True, help='Enable debug mode', inherit=False)
@command_opt('verbose', is_flag=True, help='Enable verbose logging', inherit=False)
def rerun(args):

    if os.environ.get('LEAPP_UNSUPPORTED') != '1':
        raise CommandError('This command requires the environment variable LEAPP_UNSUPPORTED="1" to be set!')

    if args.from_phase not in RERUN_SUPPORTED_PHASES:
        raise CommandError('This command is only supported for {}'.format(', '.join(RERUN_SUPPORTED_PHASES)))

    context = str(uuid.uuid4())
    last_context, configuration = util.fetch_last_upgrade_context()
    phases = [chkpt['phase'] for chkpt in util.get_checkpoints(context=last_context)]
    if args.from_phase not in set(phases):
        raise CommandError('Phase {} has not been executed in the last leapp upgrade execution. '
                           'Cannot rerun not executed phase'.format(args.from_phase))

    if not last_context:
        raise CommandError('No previous upgrade run to rerun - '
                           'leapp upgrade has to be run before leapp rerun can be used')

    with get_connection(None) as db:
        e = Execution(context=context, kind='rerun', configuration=configuration)

        e.store(db)

        clone_context(last_context, context, db)
        db.execute('''
            DELETE FROM audit WHERE id IN (
                SELECT
                    audit.id          AS id
                FROM
                    audit
                JOIN
                    data_source ON data_source.id = audit.data_source_id
                WHERE
                    audit.context = ? AND audit.event = 'checkpoint'
                    AND data_source.phase LIKE 'FirstBoot%'
            );
        ''', (context,))
        db.execute('''DELETE FROM message WHERE context = ? and type = 'ErrorModel';''', (context,))

    util.archive_logfiles()
    upgrade(Namespace(  # pylint: disable=no-value-for-parameter
        resume=True,
        resume_context=context,
        only_with_tags=args.only_actors_with_tag or [],
        debug=args.debug,
        verbose=args.verbose,
        reboot=False,
        no_rhsm=False,
        nogpgcheck=False,
        channel=None,
        report_schema='1.1.0',
        whitelist_experimental=[],
        enablerepo=[]))


def register(base_command):
    """
        Registers `leapp rerun`
    """
    base_command.add_sub(rerun)
