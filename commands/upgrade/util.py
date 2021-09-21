import itertools
import json
import os
import shutil
import tarfile
from datetime import datetime

from leapp.config import get_config
from leapp.exceptions import CommandError
from leapp.repository.scan import find_and_scan_repositories
from leapp.utils.audit import get_connection, get_checkpoints, get_messages
from leapp.utils.output import report_unsupported
from leapp.utils.report import fetch_upgrade_report_messages, generate_report_file


def restore_leapp_env_vars(context):
    """
    Restores leapp environment variables from the `IPUConfig` message.
    """
    messages = get_messages(('IPUConfig',), context)
    leapp_env_vars = json.loads((messages or [{}])[0].get('message', {}).get('data', '{}')).get('leapp_env_vars', {})
    for entry in leapp_env_vars:
        os.environ[entry['name']] = entry['value']


def archive_logfiles():
    """ Archive log files from a previous run of Leapp """
    cfg = get_config()

    if not os.path.isdir(cfg.get('files_to_archive', 'dir')):
        os.makedirs(cfg.get('files_to_archive', 'dir'))

    files_to_archive = [os.path.join(cfg.get('files_to_archive', 'dir'), f)
                        for f in cfg.get('files_to_archive', 'files').split(',')
                        if os.path.isfile(os.path.join(cfg.get('files_to_archive', 'dir'), f))]

    if not os.path.isdir(cfg.get('archive', 'dir')):
        os.makedirs(cfg.get('archive', 'dir'))

    if files_to_archive:
        if os.path.isdir(cfg.get('debug', 'dir')):
            files_to_archive.append(cfg.get('debug', 'dir'))

        now = datetime.now().strftime('%Y%m%d%H%M%S')
        archive_file = os.path.join(cfg.get('archive', 'dir'), 'leapp-{}-logs.tar.gz'.format(now))

        with tarfile.open(archive_file, "w:gz") as tar:
            for file_to_add in files_to_archive:
                tar.add(file_to_add)
                if os.path.isdir(file_to_add):
                    shutil.rmtree(file_to_add, ignore_errors=True)
                try:
                    os.remove(file_to_add)
                except OSError:
                    pass
            # leapp_db is not in files_to_archive to not have it removed
            if os.path.isfile(cfg.get('database', 'path')):
                tar.add(cfg.get('database', 'path'))


def load_repositories_from(name, repo_path, manager=None):
    if get_config().has_option('repositories', name):
        repo_path = get_config().get('repositories', name)
    return find_and_scan_repositories(repo_path, manager=manager)


def load_repositories():
    manager = load_repositories_from('repo_path', '/etc/leapp/repo.d/', manager=None)
    manager.load()
    return manager


def fetch_last_upgrade_context(use_context=None):
    """
    :return: Context of the last execution
    """
    with get_connection(None) as db:
        if use_context:
            cursor = db.execute(
                "SELECT context, stamp, configuration FROM execution WHERE context = ?", (use_context,))
        else:
            cursor = db.execute(
                "SELECT context, stamp, configuration FROM execution WHERE kind = 'upgrade' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row[0], json.loads(row[2])
    return None, {}


def fetch_all_upgrade_contexts():
    """
    :return: All upgrade execution contexts
    """
    with get_connection(None) as db:
        cursor = db.execute(
            "SELECT context, stamp, configuration FROM execution WHERE kind = 'upgrade' ORDER BY id DESC")
        row = cursor.fetchall()
        if row:
            return row
    return None


def get_last_phase(context):
    checkpoints = get_checkpoints(context=context)
    if checkpoints:
        return checkpoints[-1]['phase']


def check_env_and_conf(env_var, conf_var, configuration):
    """
    Checks whether the given environment variable or the given configuration value are set to '1'
    """
    return os.getenv(env_var, '0') == '1' or configuration.get(conf_var, '0') == '1'


def generate_report_files(context):
    """
    Generates all report files for specific leapp run (txt and json format)
    """
    cfg = get_config()
    report_txt, report_json = [os.path.join(cfg.get('report', 'dir'),
                                            'leapp-report.{}'.format(f)) for f in ['txt', 'json']]
    # fetch all report messages as a list of dicts
    messages = fetch_upgrade_report_messages(context)
    generate_report_file(messages, context, report_json)
    generate_report_file(messages, context, report_txt)


def get_cfg_files(section, cfg, must_exist=True):
    """
    Provide files from particular config section
    """
    files = []
    for file_ in cfg.get(section, 'files').split(','):
        file_path = os.path.join(cfg.get(section, 'dir'), file_)
        if not must_exist or must_exist and os.path.isfile(file_path):
            files.append(file_path)
    return files


def warn_if_unsupported(configuration):
    env = os.environ
    if env.get('LEAPP_UNSUPPORTED', '0') == '1':
        devel_vars = {k: env[k] for k in env if k.startswith('LEAPP_DEVEL_')}
        report_unsupported(devel_vars, configuration["whitelist_experimental"])


def handle_output_level(args):
    """
    Set environment variables following command line arguments.
    """
    os.environ['LEAPP_DEBUG'] = '1' if args.debug else os.getenv('LEAPP_DEBUG', '0')
    if os.environ['LEAPP_DEBUG'] == '1' or args.verbose:
        os.environ['LEAPP_VERBOSE'] = '1'
    else:
        os.environ['LEAPP_VERBOSE'] = os.getenv('LEAPP_VERBOSE', '0')


def prepare_configuration(args):
    """Returns a configuration dict object while setting a few env vars as a side-effect"""
    if args.whitelist_experimental:
        args.whitelist_experimental = list(itertools.chain(*[i.split(',') for i in args.whitelist_experimental]))
        os.environ['LEAPP_EXPERIMENTAL'] = '1'
    else:
        os.environ['LEAPP_EXPERIMENTAL'] = '0'
    os.environ['LEAPP_UNSUPPORTED'] = '0' if os.getenv('LEAPP_UNSUPPORTED', '0') == '0' else '1'
    if args.no_rhsm:
        os.environ['LEAPP_NO_RHSM'] = '1'
    elif os.getenv('LEAPP_NO_RHSM') != '1':
        os.environ['LEAPP_NO_RHSM'] = os.getenv('LEAPP_DEVEL_SKIP_RHSM', '0')
    if args.enablerepo:
        os.environ['LEAPP_ENABLE_REPOS'] = ','.join(args.enablerepo)
    configuration = {
        'debug': os.getenv('LEAPP_DEBUG', '0'),
        'verbose': os.getenv('LEAPP_VERBOSE', '0'),
        'whitelist_experimental': args.whitelist_experimental or (),
    }
    return configuration


def process_whitelist_experimental(repositories, workflow, configuration, logger=None):
    for actor_name in configuration.get('whitelist_experimental', ()):
        actor = repositories.lookup_actor(actor_name)
        if actor:
            workflow.whitelist_experimental_actor(actor)
        else:
            msg = 'No such Actor: {}'.format(actor_name)
            if logger:
                logger.error(msg)
            raise CommandError(msg)
