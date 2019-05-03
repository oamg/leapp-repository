import errno

from leapp.models import OpenSshConfig, OpenSshPermitRootLogin
from leapp.libraries.stdlib import run, api


CONFIG = '/etc/ssh/sshd_config'


def line_empty(line):
    return len(line) == 0 or line.startswith('\n') or line.startswith('#')


def parse_config(config):
    """Parse OpenSSH server configuration or the output of sshd test option."""

    # RHEL7 defaults
    ret = OpenSshConfig(
        permit_root_login=[],
    )

    in_match = None
    for line in config:
        line = line.strip()
        if line_empty(line):
            continue

        el = line.split()
        if len(el) < 2:
            continue
        value = el[1]
        if el[0].lower() == 'match':
            in_match = el[1:]
            continue

        if el[0].lower() == 'permitrootlogin':
            # convert deprecated alias
            if value == "without-password":
                value = "prohibit-password"
            v = OpenSshPermitRootLogin(value=value, in_match=in_match)
            ret.permit_root_login.append(v)

        elif el[0].lower() == 'useprivilegeseparation':
            # Record only first occurence, which is effective
            if not ret.use_privilege_separation:
                ret.use_privilege_separation = value

        elif el[0].lower() == 'protocol':
            # Record only first occurence, which is effective
            if not ret.protocol:
                ret.protocol = value

        elif el[0].lower() == 'ciphers':
            # Record only first occurence, which is effective
            if not ret.ciphers:
                ret.ciphers = value

        elif el[0].lower() == 'macs':
            # Record only first occurence, which is effective
            if not ret.macs:
                ret.macs = value

    return ret


def produce_config(producer, config):
    """Produce a Leapp message with all interesting OpenSSH configuration options."""

    producer(config)


def read_sshd_config():
    """Read the actual sshd configuration file."""
    try:
        with open(CONFIG, 'r') as fd:
            return fd.readlines()
    except IOError as err:
        if err.errno != errno.ENOENT:
            error = 'Failed to read sshd_config: {}'.format(str(err))
            api.current_logger().error(error)
        return []


def read_rpm_modifications():
    """Asks RPM database whether the configuration file was modified."""

    try:
        return run(['rpm', '-Vf', CONFIG], split=True, checked=False)['stdout']
    except OSError as err:
        error = 'Failed to check the modification status of the {}: {}' \
                ''.format(CONFIG, str(err))
        api.current_logger().error(error)
        return []


def parse_config_modification(data):
    """Handle the output of rpm verify to figure out configuration file was modified."""

    # First assume it is not modified -- empty data says it is not modified
    modified = False
    for line in data:
        parts = line.split(' ')
        # The last part of the line is the actual file we care for
        if parts[-1] == CONFIG:
            # First part contains information, if the size and digest differ
            if '5' in parts[0] or 'S' in parts[0]:
                modified = True
        # Ignore any other files lurking here

    return modified


def scan_sshd(producer):
    """Parse sshd_config configuration file to create OpenSshConfig message."""

    # direct access to configuration file
    output = read_sshd_config()
    config = parse_config(output)

    # find out whether the file was modified from the one shipped in rpm
    output = read_rpm_modifications()
    config.modified = parse_config_modification(output)

    produce_config(producer, config)
