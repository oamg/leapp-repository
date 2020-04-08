import re
import os
import shutil
from leapp.libraries.stdlib import CalledProcessError, api, run

DAEMON_FILE = '/etc/frr/daemons'
#if this file sitll exists after the removal of quagga, it has been modified
CONFIG_FILE = '/etc/sysconfig/quagga.rpmsave'
QUAGGA_CONF_FILES = '/etc/quagga/'
FRR_CONF_FILES = '/etc/frr/'

def _get_config_data(path):
    ret = {}
    with open(path, 'r') as f:
        file_data = f.readlines()

        #exclude WATCH and BABELD
        data_filter = '(?!WATCH|BABELD).*_OPTS="(.*)"'
        # data that we need is always DAEMON_OPTS="data"
        search_filter = '(.*)_OPTS="(.*)"'

        if bool(file_data):
            data_regex = re.compile(r'{}'.format(data_filter))
            data = list(filter(data_regex.match, file_data))

            for line in data:
                parse = re.search(search_filter, line)
                if parse:
                    ret[parse.group(1).lower()] = parse.group(2)
    return ret

def _edit_new_config(path, active_daemons, config_data):
    with open(path, 'r') as f:
        data = f.read()

    #replace no as yes in /etc/frr/daemons
    for daemon in active_daemons:
        data = re.sub(r'{}=no'.format(daemon), r'{}=yes'.format(daemon), data, flags=re.MULTILINE)

    if bool(config_data):
        for daemon in config_data:
            data = re.sub(r'^{}_options=".*"'.format(daemon),
                r'{}_options="{}"'.format(daemon, config_data[daemon]),
                data, flags=re.MULTILINE)

    with open(path, 'w') as f:
        f.write(data)


#1. parse /etc/sysconfig/quagga.rpmsave if it exists
#2. change =no to =yes with every enabled daemon
#3. use data from data from quagga.rpmsave in new daemon file
def _change_config(quagga_facts):
    config_data = {}
    if os.path.isfile(CONFIG_FILE):
        config_data = _get_config_data(CONFIG_FILE)

    #This file should definitely exist, if not, something went wrong with the upgrade
    if os.path.isfile(DAEMON_FILE):
        _edit_new_config(DAEMON_FILE, quagga_facts.active_daemons, config_data)

#In quagga, each daemon needed to be started individually
#In frr, only frr is started as a daemon, the rest is started based on the daemons file
#So as long as at least one daemon was active in quagga, frr should be enabled
def _enable_frr(quagga_facts):
    #remove babeld?
    if quagga_facts.enabled_daemons:
        try:
            run(['systemctl', 'enable', 'frr'])
        except CalledProcessError:
            return False

    return True

#due to an error in quagga, the conf files are not deleted after uninstall
#we can copy them as they are
def _copy_config_files(src_path, dest_path):
    conf_files = os.listdir(src_path)
    for file_name in conf_files:
        full_path = os.path.join(src_path, file_name)
        if os.path.isfile(full_path):
            shutil.copy(full_path, dest_path)
            api.current_logger().debug('Copying {} to {}{}'.format(full_path, dest_path, file_name))

def process_facts(quagga_facts):
    _change_config(quagga_facts)
    _copy_config_files(QUAGGA_CONF_FILES, FRR_CONF_FILES)
    _enable_frr(quagga_facts)
