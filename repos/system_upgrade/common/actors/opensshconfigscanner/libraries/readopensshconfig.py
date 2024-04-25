import errno
import glob
import os
import shlex

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import check_file_modification
from leapp.libraries.stdlib import api
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin

CONFIG = '/etc/ssh/sshd_config'
DEPRECATED_DIRECTIVES = ['showpatchlevel']


def line_empty(line):
    return len(line) == 0 or line.startswith('\n') or line.startswith('#')


def parse_config(config, base_config=None, current_cfg_depth=0):
    """
    Parse OpenSSH server configuration or the output of sshd test option.

    :param Optional[OpenSshConfig] base_config: Base configuration that is extended with configuration options from
    current file.

    :param int current_cfg_depth: Internal counter for how many includes were already followed.
    """

    if current_cfg_depth > 16:
        # This should really never happen as it would mean the SSH server won't
        # start anyway on the old system.
        error = 'Too many recursive includes while parsing sshd_config'
        api.current_logger().error(error)
        return None

    ret = base_config
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
            # the option can have several space-separated filenames with glob wildcards
            for pattern in shlex.split(' '.join(el[1:])):
                if pattern[0] != '/' and pattern[0] != '~':
                    pattern = os.path.join('/etc/ssh/', pattern)
                files_matching_include_pattern = glob.glob(pattern)
                # OpenSSH sorts the files lexicographically
                files_matching_include_pattern.sort()
                for included_config_file in files_matching_include_pattern:
                    output = read_sshd_config(included_config_file)
                    if parse_config(output, base_config=ret, current_cfg_depth=current_cfg_depth + 1) is None:
                        raise StopActorExecutionError(
                            'Failed to parse sshd configuration file',
                            details={'details': 'Too many recursive includes while parsing {}.'
                                     .format(included_config_file)}
                        )

        elif el[0].lower() in DEPRECATED_DIRECTIVES:
            # Filter out duplicate occurrences of the same deprecated directive
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
