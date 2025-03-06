import functools
import itertools
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime

from leapp.cli.commands import command_utils
from leapp.cli.commands.config import get_config
from leapp.exceptions import CommandError
from leapp.repository.scan import find_and_scan_repositories
from leapp.utils import audit
from leapp.utils.audit import get_checkpoints, get_connection, get_messages
from leapp.utils.output import report_unsupported
from leapp.utils.report import fetch_upgrade_report_messages, generate_report_file

EXPERIMENTAL_FEATURES = {
    'livemode': [
        'live_image_generator',
        'live_mode_config_scanner',
        'live_mode_reporter',
        'prepare_live_image',
        'emit_livemode_requirements',
        'remove_live_image',
    ]
}
""" Maps experimental features to a set of experimental actors that need to be enabled. """


def get_help_str_with_avail_experimental_features():
    if EXPERIMENTAL_FEATURES:
        return ', '.join(EXPERIMENTAL_FEATURES)
    return 'There are no experimental features available'


def disable_database_sync():
    def disable_db_sync_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            saved = os.environ.get('LEAPP_DEVEL_DATABASE_SYNC_OFF', None)
            try:
                os.environ['LEAPP_DEVEL_DATABASE_SYNC_OFF'] = '1'
                return f(*args, **kwargs)
            finally:
                os.environ.pop('LEAPP_DEVEL_DATABASE_SYNC_OFF')
                if saved:
                    os.environ['LEAPP_DEVEL_DATABASE_SYNC_OFF'] = saved
        return wrapper

    if not os.environ.get('LEAPP_DATABASE_FORCE_SYNC_ON', None):
        audit.create_connection = disable_db_sync_decorator(audit.create_connection)


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
    return None


def check_env_and_conf(env_var, conf_var, configuration):
    """
    Checks whether the given environment variable or the given configuration value are set to '1'
    """
    return os.getenv(env_var, '0') == '1' or configuration.get(conf_var, '0') == '1'


def generate_report_files(context, report_schema):
    """
    Generates all report files for specific leapp run (txt and json format)
    """
    cfg = get_config()
    report_txt, report_json = [os.path.join(cfg.get('report', 'dir'),
                                            'leapp-report.{}'.format(f)) for f in ['txt', 'json']]
    # fetch all report messages as a list of dicts
    messages = fetch_upgrade_report_messages(context)
    generate_report_file(messages, context, report_txt, report_schema)
    generate_report_file(messages, context, report_json, report_schema)


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


# NOTE(ivasilev) Please make sure you are not calling prepare_configuration after first reboot.
# If called as leapp upgrade --resume this will happily crash in target version container for
# the latest supported release because of target_version discovery attempt.
def prepare_configuration(args):
    """Returns a configuration dict object while setting a few env vars as a side-effect"""

    if args.whitelist_experimental:
        args.whitelist_experimental = list(itertools.chain(*[i.split(',') for i in args.whitelist_experimental]))
        os.environ['LEAPP_EXPERIMENTAL'] = '1'
    else:
        os.environ['LEAPP_EXPERIMENTAL'] = '0'
        args.whitelist_experimental = []

    for experimental_feature in set(args.enable_experimental_feature):
        # It might happen that there are no experimental features, which would allow user
        # to pass us any string as an experimental feature.
        if experimental_feature not in EXPERIMENTAL_FEATURES:
            continue

        actors_needed_for_feature = EXPERIMENTAL_FEATURES[experimental_feature]
        args.whitelist_experimental.extend(actors_needed_for_feature)
    if args.enable_experimental_feature:
        os.environ['LEAPP_EXPERIMENTAL'] = '1'

    os.environ['LEAPP_UNSUPPORTED'] = '0' if os.getenv('LEAPP_UNSUPPORTED', '0') == '0' else '1'
    if args.no_rhsm:
        os.environ['LEAPP_NO_RHSM'] = '1'
    elif not os.path.exists('/usr/sbin/subscription-manager'):
        os.environ['LEAPP_NO_RHSM'] = '1'
    elif os.getenv('LEAPP_NO_RHSM') != '1':
        os.environ['LEAPP_NO_RHSM'] = os.getenv('LEAPP_DEVEL_SKIP_RHSM', '0')

    if args.no_insights_register:
        os.environ['LEAPP_NO_INSIGHTS_REGISTER'] = '1'

    if args.enablerepo:
        os.environ['LEAPP_ENABLE_REPOS'] = ','.join(args.enablerepo)

    if os.environ.get('LEAPP_NO_RHSM', '0') == '1' or args.no_rhsm_facts:
        os.environ['LEAPP_NO_RHSM_FACTS'] = '1'

    if args.channel:
        os.environ['LEAPP_TARGET_PRODUCT_CHANNEL'] = args.channel
    elif 'LEAPP_TARGET_PRODUCT_CHANNEL' not in os.environ:
        os.environ['LEAPP_TARGET_PRODUCT_CHANNEL'] = 'ga'

    if args.iso:
        os.environ['LEAPP_TARGET_ISO'] = args.iso
    target_iso_path = os.environ.get('LEAPP_TARGET_ISO')
    if target_iso_path:
        # Make sure we convert rel paths into abs ones while we know what CWD is
        os.environ['LEAPP_TARGET_ISO'] = os.path.abspath(target_iso_path)

    if args.nogpgcheck:
        os.environ['LEAPP_NOGPGCHECK'] = '1'

    # Check upgrade path and fail early if it's unsupported
    target_version, flavor = command_utils.vet_upgrade_path(args)
    os.environ['LEAPP_UPGRADE_PATH_TARGET_RELEASE'] = target_version
    os.environ['LEAPP_UPGRADE_PATH_FLAVOUR'] = flavor

    current_version = command_utils.get_os_release_version_id('/etc/os-release')
    os.environ['LEAPP_IPU_IN_PROGRESS'] = '{source}to{target}'.format(
        source=command_utils.get_major_version(current_version),
        target=command_utils.get_major_version(target_version)
    )

    configuration = {
        'debug': os.getenv('LEAPP_DEBUG', '0'),
        'verbose': os.getenv('LEAPP_VERBOSE', '0'),
        'whitelist_experimental': args.whitelist_experimental or (),  # Modified to also contain exp. features
        'environment': {env: os.getenv(env) for env in os.environ if env.startswith('LEAPP_')},
        'cmd': sys.argv,
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
