import os

from leapp.libraries.stdlib import api, CalledProcessError, run

DEFAULT_OPENSSL_CONF = '/etc/pki/tls/openssl.cnf'
OPENSSL_CONF_RPMNEW = '{}.rpmnew'.format(DEFAULT_OPENSSL_CONF)
OPENSSL_CONF_BACKUP = '{}.leappsave'.format(DEFAULT_OPENSSL_CONF)


def _is_openssl_modified():
    """
    Return True if modified in any way
    """
    # NOTE(pstodulk): this is different from the approach in scansourcefiles,
    # where we are interested about modified content. In this case, if the
    # file is modified in any way, let's do something about that..
    try:
        run(['rpm', '-Vf', DEFAULT_OPENSSL_CONF])
    except CalledProcessError:
        return True
    return False


def _safe_mv_file(src, dst):
    """
    Move the file from src to dst. Return True on success, otherwise False.
    """
    try:
        run(['mv', src, dst])
    except CalledProcessError:
        return False
    return True


def process():
    if not _is_openssl_modified():
        return
    if not os.path.exists(OPENSSL_CONF_RPMNEW):
        api.current_logger().debug('The {} file is modified, but *.rpmsave not found. Cannot do anything.')
        return
    if not _safe_mv_file(DEFAULT_OPENSSL_CONF, OPENSSL_CONF_BACKUP):
        # NOTE(pstodulk): One of reasons could be the file is missing, however
        # that's not expected to happen at all. If the file is missing before
        # the upgrade, it will be installed by new openssl* package
        api.current_logger().error(
            'Could not back up the {} file. Skipping other actions.'
            .format(DEFAULT_OPENSSL_CONF)
        )
        return
    if not _safe_mv_file(OPENSSL_CONF_RPMNEW, DEFAULT_OPENSSL_CONF):
        # unexpected, it's double seatbelt
        api.current_logger().error('Cannot apply the new openssl configuration file! Restore it from the backup.')
        if not _safe_mv_file(OPENSSL_CONF_BACKUP, DEFAULT_OPENSSL_CONF):
            api.current_logger().error('Cannot restore the openssl configuration file!')
