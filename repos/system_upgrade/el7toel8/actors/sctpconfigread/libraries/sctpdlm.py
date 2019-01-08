#
# Functions for probing SCTP usage by DLM
#
import re

from six.moves.configparser import SafeConfigParser

from leapp.libraries.stdlib import api


def check_dlm_cfgfile():
    """Parse DLM config file"""
    fname = "/etc/dlm/dlm.conf"

    try:
        with open(fname, 'r') as fp:
            cfgs = '[dlm]\n' + fp.read()
    except (OSError, IOError):
        return False

    cfg = SafeConfigParser()
    try:
        cfg.read_string(cfgs)
    except AttributeError:
        # Python2 ConfigParser doesn't have cfg.read_string
        from cStringIO import StringIO
        cfg.readfp(StringIO(cfgs))

    if not cfg.has_option('dlm', 'protocol'):
        return False

    proto = cfg.get('dlm', 'protocol').lower()
    return proto in ['sctp', 'detect', '1', '2']


def check_dlm_sysconfig():
    """Parse /etc/sysconfig/dlm"""
    regex = re.compile('^[^#]*DLM_CONTROLD_OPTS.*=.*(?:--protocol|-r)[ =]*([^"\' ]+).*', re.IGNORECASE)

    try:
        with open('/etc/sysconfig/dlm', 'r') as fp:
            lines = fp.readlines()
    except (OSError, IOError):
        return False

    for line in lines:
        if regex.match(line):
            proto = regex.sub('\\1', line).lower().strip()
            if proto in ['sctp', 'detect']:
                return True

    return False


def is_dlm_using_sctp():
    if check_dlm_cfgfile():
        api.current_logger().info('DLM is configured to use SCTP on dlm.conf.')
        return True

    if check_dlm_sysconfig():
        api.current_logger().info('DLM is configured to use SCTP on sysconfig.')
        return True

    return False
