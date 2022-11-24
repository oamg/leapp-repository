from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class DNFWorkaround(Model):
    """
    DNFWorkaround is used to register scripts, that have to be executed to apply modifications to the system,
    just before DNF performs a transaction in order for it to succeed.

    As an example in the case of the RHEL7 to RHEL8 upgrade, we have to execute a script to fixup the way how
    yum and dnf symlinks are created as they cannot be replaced by RPM. To solve this we have created the
    handleyumconfig tool in the system_upgrade/el7toel8 repository and register the workaround with the
    registeryumadjustment actor.
    """
    topic = SystemInfoTopic

    script_path = fields.String()
    """
    Absolute path to a bash script to execute
    """

    script_args = fields.List(fields.String(), default=[])
    """
    Arguments with which the script should be executed

    In case that an argument contains a whitespace or an escapable character,
    the argument must be already treated correctly. e.g.
        `script_args = ['-i', 'my\\ string']
    """

    display_name = fields.String()
    """
    Name to display for this script when executed
    """
