from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# The main SSHD configuration file
SSHD_CONFIG = '/etc/ssh/sshd_config'

# The include directive needed, taken from RHEL9 sshd_config with leapp comment
INCLUDE = 'Include /etc/ssh/sshd_config.d/*.conf'
INCLUDE_BLOCK = ''.join(('# Added by leapp during upgrade from RHEL8 to RHEL9\n', INCLUDE, '\n'))


def prepend_string_if_not_present(f, content, check_string):
    """
    This reads the open file descriptor and checks for presense of the `check_string`.
    If not present, the `content` is prepended to the original content of the file and
    result is written.
    Note, that this requires opened file for both reading and writing, for example with:

        with open(path, r+') as f:
    """
    lines = f.readlines()
    for line in lines:
        if line.lstrip().startswith(check_string):
            # The directive is present
            return

    # prepend it otherwise, also with comment
    f.seek(0)
    f.write(''.join((content, ''.join(lines))))


def process(openssh_messages):
    """
    The main logic of the actor:
     * read the configuration file message
     * skip if no action is needed
       * package not installed
       * the configuration file was not modified
     * insert the include directive if it is not present yet
    """
    config = next(openssh_messages, None)
    if list(openssh_messages):
        api.current_logger().warning('Unexpectedly received more than one OpenSshConfig message.')
    if not config:
        raise StopActorExecutionError(
            'Could not check openssh configuration', details={'details': 'No OpenSshConfig facts found.'}
        )

    # If the package is not installed, there is no need to do anything
    if not has_package(InstalledRedHatSignedRPM, 'openssh-server'):
        return

    # If the configuration file was not modified, the rpm update will bring the new
    # changes by itself
    if not config.modified:
        return

    # otherwise prepend the Include directive to the main sshd_config
    api.current_logger().debug('Adding the Include directive to {}.'
                               .format(SSHD_CONFIG))
    try:
        with open(SSHD_CONFIG, 'r+') as f:
            prepend_string_if_not_present(f, INCLUDE_BLOCK, INCLUDE)
    except (OSError, IOError) as error:
        api.current_logger().error('Failed to modify the file {}: {} '.format(SSHD_CONFIG, error))
