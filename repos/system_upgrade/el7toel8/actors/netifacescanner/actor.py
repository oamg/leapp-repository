from leapp.actors import Actor
from leapp.models import IfaceResult, IfacesInfo
from leapp.tags import FactsPhaseTag
import subprocess
import os
import re
import sys


class NetIfaceScanner(Actor):
    name = 'net_iface_scanner'
    description = 'This actor provides a basic info about network interfaces settings.'
    consumes = ()
    produces = (IfaceResult,)
    tags = (FactsPhaseTag,)

    def process(self):
        iface_info = self.return_ifs_info()
        self.produce(iface_info)
        self.log.info("Finished scanning network interfaces")
        pass

    def get_ifaces_names(self):
        # Getting the list of interface names, independent from run-time naming.
        sys_command = ['find', '/sys/devices/', '-name', 'net', '-type', 'd']
        ifacepaths = []
        try:
            dirs = subprocess.check_output((sys_command),
                                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as command_failed:
            self.log.warning("Could not get the interface names" + command_failed.output)
            sys.exit(1)
        dirs = dirs.decode('utf-8')
        dirs = dirs.splitlines()
        for direct in dirs:
            ifacelist = os.listdir(direct)
            for iface in ifacelist:
                iface_path = os.path.join(direct, iface)
                ifacepaths.append(iface_path)
                ifacepaths = sorted(ifacepaths)
        return ifacepaths

    def get_net_driver(self, iface):
        iface_stats = subprocess.Popen(('ethtool', '-i', iface),
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        iface_stats, err = iface_stats.communicate()
        driver = re.search(r"(driver):\s+(.*)$", iface_stats,
                           flags=re.MULTILINE)
        if driver is not None:
            driver = driver.group(2)
        else:
            driver = "None"
        return driver

    def get_persistent_hwaddr(self, iface):
        ethinf = subprocess.Popen(('ethtool', '-P', iface),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ethinf, err = ethinf.communicate()
        if not err:
            # return "Permanent address"
            return ethinf.split()[2]
        return "None"

    def return_ifs_info(self):
        if_paths = self.get_ifaces_names()
        journal = subprocess.Popen(('journalctl', '-xe', '--no-tail'), stdout=subprocess.PIPE)
        journal, err = journal.communicate()
        result = IfaceResult()
        # Getting info about bonding and bridges
        for if_path in if_paths:
            for fname in os.listdir(if_path):
                if fname == 'bonding':
                    bond_status = 'master'
                    break
                elif fname == 'bonding_slave':
                    bond_status = 'slave'
                    break
                else:
                    bond_status = 'None'

            for fname in os.listdir(if_path):
                if fname == 'bridge':
                    bridge_status = 'master'
                    break
                if fname == 'master':
                    bridge_status = 'slave'
                    break
                else:
                    bridge_status = 'None'

            if_name = os.path.basename(if_path)
            driver = self.get_net_driver(if_name)
            hwaddr = self.get_persistent_hwaddr(if_name)
            network_script = self.get_conf_file(if_name)
            route_info = self.get_route_info(if_name)
            if route_info == '':
                route_info = 'None'
            else:
                route_info = route_info.strip()
            ipv4_string = re.compile(r"^(IPADDR)\s*=\s*\"?(.*)\"?$")
            boot_string = re.compile(r"^(BOOTPROTO)\s*=\s*\"?(.*)\"?$")
            if network_script is not None:
                # Determining if ip address is obtained via dhcp and getting the ip address
                boot_proto = self.get_last_occurence(boot_string, network_script)
                if isinstance(boot_proto, list):
                    boot_proto = boot_proto[-1][1]
                if boot_proto.lower() == "dhcp":
                    ip = self.get_ips(if_name, journal)
                else:
                    ip = self.get_last_occurence(ipv4_string, network_script)
                    if isinstance(ip, list):
                        ip = ip[-1][1]
                    else:
                        ip = "None"
                result.items.append(IfacesInfo(
                    if_name=if_name,
                    hwaddr=hwaddr,
                    driver=driver,
                    bond_status=bond_status,
                    bridge_status=bridge_status,
                    route_info=route_info,
                    ipv4addr=ip))
                runtime_hw = self.get_runtime_hws(if_name)
                if runtime_hw:
                    if runtime_hw != hwaddr:
                        self.log.info("The persistent hwaddr of interface %s is %s, but runtime hwaddr is %s"
                                      % (if_name, hwaddr, runtime_hw))
            else:
                self.log.warning("There is missing configuration file for %s, skipping" % if_name)
        return result

    def get_conf_file(self, file_name):
        script_dir = "/etc/sysconfig/network-scripts"
        confile = "ifcfg-" + file_name
        if (confile) in os.listdir(script_dir):
            return os.path.join(script_dir, confile)

    def get_ips(self, if_name, data):
        ip = ''
        pattern = r".*\(" + if_name + r"\):\s+address\s+(.*)"
        match_proto = re.search(pattern, data)
        if match_proto:
            ip = match_proto.group(1)
        return ip

    def get_last_occurence(self, pattern, input_file):
        if os.path.exists(input_file):
            with open(input_file, 'rb') as inf:
                protocol = ''
                for data in inf:
                    match_proto = re.findall(pattern, data)
                    if match_proto:
                        protocol = match_proto
            return protocol

    def get_runtime_hws(self, iface):
        data = subprocess.Popen(('ip', 'addr', 'show', 'dev', iface), stdout=subprocess.PIPE)
        data, err = data.communicate()
        pattern = r"link\/ether\s(.*)\sbrd.*"
        match = re.search(pattern, data)
        if match:
            match = match.group(1)
            return match

    def get_route_info(self, if_name):
        routeinfo = subprocess.Popen(('ip', 'route', 'show', 'dev', if_name),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        routeinfo, err = routeinfo.communicate()
        return routeinfo
