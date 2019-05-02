import errno
import re

from leapp.libraries.stdlib import api
from leapp.models import DaemonList, TcpWrappersFacts

CONFIG_FILES = ['/etc/hosts.allow', '/etc/hosts.deny']


def _read_file(path):
    with open(path, 'r') as f:
        return f.read()


def _get_lines(content):
    content = re.sub(r'\\\n', '', content)
    return content.split('\n')


def _is_comment(line):
    return len(line) == 0 or line.isspace() or line.startswith('#')


def _get_daemon_list_in_line(line):
    daemon_list = line.split(':', 1)[0]
    daemon_list = re.split(',| |\t', daemon_list)
    daemon_list = [word for word in daemon_list if len(word) > 0]
    return DaemonList(value=daemon_list)


def _get_daemon_lists_in_file(path, read_func=_read_file):
    ret = []
    try:
        content = read_func(path)
    except IOError as e:
        if e.errno != errno.ENOENT:
            api.current_logger().warning('Failed to read %s: %s' % (path, e))
        return ret
    lines = [line for line in _get_lines(content) if not _is_comment(line)]
    for line in lines:
        ret.append(_get_daemon_list_in_line(line))
    return ret


def _get_daemon_lists(read_func=_read_file):
    daemon_lists = []
    for path in CONFIG_FILES:
        daemon_lists.extend(_get_daemon_lists_in_file(path, read_func=read_func))
    return daemon_lists


def get_tcp_wrappers_facts(read_func=_read_file):
    daemon_lists = _get_daemon_lists(read_func=read_func)
    return TcpWrappersFacts(daemon_lists=daemon_lists)
