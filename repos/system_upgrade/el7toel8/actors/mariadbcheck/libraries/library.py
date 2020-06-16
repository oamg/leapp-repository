import os
from leapp.models import InstalledRedHatSignedRPM
from leapp import reporting
from leapp.libraries.stdlib import CalledProcessError, api, run


def parse_mycnf(config_file):
    """ get used mysql options """
    try:
        output = run([
            '/usr/bin/my_print_defaults',
            '-c', config_file,
            '--mysqld'
        ], split=True)['stdout']
    except CalledProcessError:
        api.current_logger().warning('Unable to obtain MySQL local configuration.')
        return None
    return [line.split('=', 1) for line in output.splitlines()]


def get_plugin_dir(config):
    """ return plugin dir """

    for entry in config:
        if entry[0] == 'plugin-dir':
            return entry[1]
    # RHEL7 default plugin dir
    return "/usr/lib64/mysql/plugin"


def get_unsupported_plugins(plugin_dir):
    """ return list of unsupported plugins """


    # 103 means mariadb version 10.3 
    plugins_103 = [
        'adt_null.so', 'auth_0x0100.so', 'auth_ed25519.so', 'auth_gssapi_client.so',
        'auth_gssapi.so', 'auth_pam.so', 'auth_socket.so', 'auth_test_plugin.so',
        'client_ed25519.so', 'debug_key_management.so', 'dialog_examples.so',
        'dialog.so', 'disks.so', 'example_key_management.so', 'file_key_management.so',
        'ha_example.so', 'ha_federated.so', 'handlersocket.so', 'ha_spider.so',
        'ha_test_sql_discovery.so', 'libdaemon_example.so', 'locales.so',
        'metadata_lock_info.so', 'mypluglib.so', 'mysql_clear_password.so',
        'qa_auth_client.so', 'qa_auth_interface.so', 'qa_auth_server.so',
        'query_cache_info.so', 'query_response_time.so', 'remote_io.so',
        'server_audit.so', 'sha256_password.so', 'simple_password_check.so',
        'sql_errlog.so', 'test_versioning.so', 'wsrep_info.so',
        'daemon_example.ini' # TODO what with ini
    ]
    if not os.path.isdir(plugin_dir):
        # TODO cant check plugins
        api.current_logger().warning('Unable to locate MySQL plugin directory.')
        return []
    plugins_installed = os.listdir(plugin_dir)

    return [plugin for plugin in plugins_installed if plugin not in plugins_103]


def get_warn_options(used_opts):
    """ 
        Return tuple(warn_changed[], warn_renamed{from: to}, warn_removed[]) of config options somehow changed in rhel8
        https://mariadb.com/kb/en/library/upgrading-from-mariadb-55-to-mariadb-100/#options-that-have-been-removed-or-renamed 
    """

    options_changed_def = [
        'aria-sort-buffer-size', 'back_log', 'innodb-buffer-pool-instances',
        'innodb-concurrency-tickets', 'innodb-log-file-size',
        'innodb-old-blocks-time', 'innodb-open-files', 
        'innodb-purge-batch-size', 'innodb-undo-logs',
        'max-connect-errors', 'max-relay-log-size', 'myisam-sort-buffer-size',
        'optimizer-switch'
    ]
    options_renamed = {
        'engine-condition-pushdown': 'set optimizer_switch="engine_condition_pushdown=on"',
        'innodb-fast-checksum': 'innodb-checksum-algorithm',
        'innodb-flush-neighbor-pages': 'innodb-flush-neighbors',
        'innodb-stats-auto-update': 'innodb-stats-auto-recalc'
    }
    options_not_in_103 = [
        'innodb-adaptive-flushing-method', 'innodb-autoextend-increment',
        'innodb-blocking-buffer-pool-restore', 'innodb-buffer-pool-pages',
        'innodb-buffer-pool-pages-blob', 'innodb-buffer-pool-pages-index',
        'innodb-buffer-pool-restore-at-startup', 'innodb-buffer-pool-shm-checksum',
        'innodb-buffer-pool-shm-key', 'innodb-checkpoint-age-target',
        'innodb-dict-size-limit', 'innodb-doublewrite-file',
        'innodb-ibuf-accel-rate', 'innodb-ibuf-active-contract',
        'innodb-ibuf-max-size', 'innodb-import-table-from-xtrabackup',
        'innodb-index-stats', 'innodb-lazy-drop-table', 
        'innodb-merge-sort-block-size', 'innodb-persistent-stats-root-page',
        'innodb-read-ahead', 'innodb-recovery-stats',
        'innodb-recovery-update-relay-log', 'innodb-stats-update-need-lock',
        'innodb-sys-stats', 'innodb-table-stats', 'innodb-thread-concurrency-timer-based',
        'innodb-use-sys-stats-table', 'xtradb-admin-command'
    ]

    warn_changed = []
    warn_renamed = {}
    warn_removed = []

    # TODO this could check also values
    for used_opt in used_opts:
        option_name = used_opt[0]

        for changed_opt in options_changed_def:
            if option_name == changed_opt:
                warn_changed.append(changed_opt)

        for renamed_opt in options_renamed:
            if option_name == renamed_opt:
                warn_renamed[renamed_opt] = options_renamed[renamed_opt]

        for removed_opt in options_not_in_103:
            if option_name == removed_opt:
                warn_removed.append(removed_opt)

    return (warn_changed, warn_renamed, warn_removed)


def generate_report():
    """ Generate reports informing user about possible manual intervention requirements """

    DOC_URL = 'https://access.redhat.com/articles/4055661'
    MYCNF = '/etc/my.cnf'

    config = parse_mycnf(MYCNF)
    unsupported_plugins = get_unsupported_plugins(get_plugin_dir(config))
    (opts_changed, opts_renamed, opts_removed) = get_warn_options(config)

    # Show documentation url if mariadb-server installed
    title = 'MariaDB server installation detected'
    summary = 'MariaDB server will be upgraded. Additional steps might be required.\n\n'

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Tags([reporting.Tags.SERVICES]),
        reporting.ExternalLink(title='Read more here.', url=DOC_URL)
        ])

    if unsupported_plugins:
        title = 'MariaDB server unsupported plugins detected'
        summary = 'Following installed plugins won\'t be part of MariaDB distribution ' \
                  'after upgrade:\n{}'.format(", ".join(unsupported_plugins))

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES])
            ])

    if opts_changed:
        title = 'MariaDB server changed default values of some options'
        summary = 'Following config options changed default value:\n{}'.format(
            ", ".join(opts_changed)
        )

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Tags([reporting.Tags.SERVICES])
            ])

    if opts_renamed:
        title = 'MariaDB server renamed some options'
        severity = 'high'
        summary = 'Following used config options were renamed:\n{}'.format(
            ", ".join(opts_renamed)
        )

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES])
            ])

    if opts_removed:
        title = 'MariaDB server removed some options'
        severity = 'high'
        summary = 'Following used config options were removed:\n{}'.format(
            ", ".join(opts_removed)
        )

        reporting.create_report([
            reporting.Title(title),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SERVICES])
            ])
