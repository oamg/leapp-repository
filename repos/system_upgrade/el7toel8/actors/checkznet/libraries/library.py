
from leapp.libraries.stdlib import run


# TODO: https://github.com/oamg/leapp-repository/issues/395
def get_kernel_cmdline():
    with open('/proc/cmdline') as cmdline:
        return cmdline.read()


def znet_is_set(cmdline):
    return 'rd.znet' in cmdline


def vlan_is_used():
    # if stdout is empty, vlan is not used
    # NOTE: not sure about macvlan, ...
    stdout = run(['ip', 'link', 'show', 'type', 'vlan'])['stdout']
    return bool(stdout)
