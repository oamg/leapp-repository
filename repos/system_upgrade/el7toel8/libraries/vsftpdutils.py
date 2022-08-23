import errno
import hashlib

from leapp.libraries.stdlib import api

VSFTPD_CONFIG_DIR = '/etc/vsftpd'
VSFTPD_DEFAULT_CONFIG_PATH = '/etc/vsftpd/vsftpd.conf'
STRICT_SSL_READ_EOF = 'strict_ssl_read_eof'
TCP_WRAPPERS = 'tcp_wrappers'


def read_file(path):
    """
    Read a file in text mode and return the contents.

    :param path: File path
    """
    with open(path, 'r') as f:
        return f.read()


def get_config_contents(path, read_func=read_file):
    """
    Try to read a vsftpd configuration file

    Try to read a vsftpd configuration file, log a warning if an error happens.
    :param path: File path
    :param read_func: Function to use to read the file. This is meant to be overridden in tests.
    :return: File contents or None, if the file could not be read
    """
    try:
        return read_func(path)
    except IOError as e:
        if e.errno != errno.ENOENT:
            api.current_logger().warning('Failed to read vsftpd configuration file: %s' % e)
        return None


def get_default_config_hash(read_func=read_file):
    """
    Read the default vsftpd configuration file (/etc/vsftpd/vsftpd.conf) and return its hash.

    :param read_func: Function to use to read the file. This is meant to be overridden in tests.
    :return SHA1 hash of the configuration file, or None if the file could not be read.
    """
    content = get_config_contents(VSFTPD_DEFAULT_CONFIG_PATH, read_func=read_func)
    if content is None:
        return None
    content = content.encode(encoding='utf-8')
    h = hashlib.sha1(content)
    return h.hexdigest()
