import re

from leapp.libraries.stdlib import api, run, CalledProcessError


def list_selinux_modules():
    """
    Produce list of SELinux policy modules

    Returns list of tuples (name,priority)
    """
    try:
        semodule = run(['semodule', '-lfull'], split=True)
    except CalledProcessError:
        api.current_logger().warning('Cannot get list of selinux modules')
        return []

    modules = []
    for module in semodule.get("stdout", []):
        # Matching line such as "100 zebra             pp"
        #                       "400 virt_supplementary pp disabled"
        # "<priority> <module name> <module type - pp/cil> [disabled]"
        m = re.match(r'([0-9]+)\s+([\w-]+)\s+([\w-]+)(?:\s+([\w]+))?\s*\Z', module)
        if not m:
            # invalid output of "semodule -lfull"
            api.current_logger().warning('Invalid output of "semodule -lfull": %s', module)
            continue
        modules.append((m.group(2), m.group(1)))

    return modules
