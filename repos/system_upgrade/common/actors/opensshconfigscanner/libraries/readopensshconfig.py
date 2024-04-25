import errno
import glob
import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import check_file_modification
from leapp.libraries.stdlib import api
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin

CONFIG = '/etc/ssh/sshd_config'
DEPRECATED_DIRECTIVES = ['showpatchlevel']


def line_empty(line):
    return len(line) == 0 or line.startswith('\n') or line.startswith('#')


def parse_config(config, ret=None, depth=0):
    """Parse OpenSSH server configuration or the output of sshd test option."""

    if depth > 16:
        # This should really never happen as it would mean the SSH server won't
        # start anyway on the old system.
        error = 'Too many recursive includes while parsing sshd_config'
        api.current_logger().error(error)
        return None

    if ret is None:
        # RHEL7 defaults
        ret = OpenSshConfig(
            permit_root_login=[],
            deprecated_directives=[]
        )
        # TODO(Jakuje): Do we need different defaults for RHEL8?

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
            # Record only first occurrence, which is effective
            if not ret.use_privilege_separation:
                ret.use_privilege_separation = value

        elif el[0].lower() == 'protocol':
            # Record only first occurrence, which is effective
            if not ret.protocol:
                ret.protocol = value

        elif el[0].lower() == 'ciphers':
            # Record only first occurrence, which is effective
            if not ret.ciphers:
                ret.ciphers = value

        elif el[0].lower() == 'macs':
            # Record only first occurrence, which is effective
            if not ret.macs:
                ret.macs = value

        elif el[0].lower() == 'subsystem':
            # Record only first occurrence, which is effective
            if el[1].lower() == 'sftp' and len(el) > 2 and not ret.subsystem_sftp:
                # here we need to record all remaining items as command and arguments
                ret.subsystem_sftp = ' '.join(el[2:])

        elif el[0].lower() == 'include':
            # recursively parse the given file or files referenced by this option
            pattern = el[1]
            if pattern[0] != '/' and pattern[0] != '~':
                pattern = os.path.join('/etc/ssh/', pattern)
            # NOTE that OpenSSH sorts the files lexicographically
            files = glob.glob(pattern)
            files.sort()
            for f in files:
                output = read_sshd_config(f)
                if parse_config(output, ret, depth + 1) is None:
                    raise StopActorExecutionError(
                        'Failed to parse sshd configuration file: ',
                        details={'details': 'Too many recursive includes while parsing {}.'.format(f)}
                    )

        elif el[0].lower() in DEPRECATED_DIRECTIVES:
            # Filter out duplicit occurrences of the same deprecated directive
            if el[0].lower() not in ret.deprecated_directives:
                # Use the directive in the form as found in config for user convenience
                ret.deprecated_directives.append(el[0])
    return ret


def produce_config(producer, config):
    """Produce a Leapp message with all interesting OpenSSH configuration options."""

    producer(config)


def read_sshd_config(config):
    """Read the actual sshd configuration file."""
    try:
        with open(config, 'r') as fd:
            return fd.readlines()
    except IOError as err:
        if err.errno != errno.ENOENT:
            error = 'Failed to read sshd_config: {}'.format(str(err))
            api.current_logger().error(error)
        return []


def scan_sshd(producer):
    """Parse sshd_config configuration file to create OpenSshConfig message."""

    # direct access to configuration file
    output = read_sshd_config(CONFIG)
    config = parse_config(output)

    # find out whether the file was modified from the one shipped in rpm
    config.modified = check_file_modification(CONFIG)

    produce_config(producer, config)
