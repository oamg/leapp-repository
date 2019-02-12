from leapp.libraries.stdlib import api
from leapp.libraries.stdlib import CalledProcessError
from leapp.libraries.stdlib import run

CMDS = [
    ['mkdir', '-p', '/etc/dnf'],
    ['cp', '-af', '/etc/yum/*', '/etc/dnf/'],
    ['rm', '-rf', '/etc/yum/pluginconf.d', '/etc/yum/protected.d', '/etc/yum/vars'],
    ['ln', '-s', '/etc/dnf/plugins/', '/etc/yum/pluginconf.d'],
    ['ln', '-s', '/etc/dnf/protected.d/', '/etc/yum/protected.d'],
    ['ln', '-s', '/etc/dnf/vars/', '/etc/yum/vars']
]


def run_cmd(cmd):
    """
    Carry out the command

    :param cmd:
    :return: Yellow Flag flag
    """
    yellow_flag = False
    try:
        run(cmd)
    except (CalledProcessError, OSError) as error:
        api.current_logger().warning('Yum upgradability may be affected:' + str(error))
        yellow_flag = True
    return yellow_flag


def secure_yum_upgradability():
    """
    Copy yum v3 configuration to yum v4 /etc/dnf directory

    :return: Yellow Flag flag
    """

    yellow_flag = False
    for cmd in CMDS:
        if run_cmd(cmd):
            yellow_flag = True

    return yellow_flag
