import os
import re
from shutil import rmtree

from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxModule, SELinuxCustom, SELinuxFacts, SELinuxRequestRPMs, RpmTransactionTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import run, CalledProcessError

WORKING_DIRECTORY = '/tmp/selinux/'

# types and attributes that where removed between RHEL 7 and 8
REMOVED_TYPES_=["base_typeattr_15","direct_run_init","gpgdomain","httpd_exec_scripts","httpd_user_script_exec_type","ibendport_type","ibpkey_type","pcmcia_typeattr_2","pcmcia_typeattr_3","pcmcia_typeattr_4","pcmcia_typeattr_5","pcmcia_typeattr_6","pcmcia_typeattr_7","sandbox_caps_domain","sandbox_typeattr_2","sandbox_typeattr_3","sandbox_typeattr_4","server_ptynode","systemctl_domain","user_home_content_type","userhelper_type","cgdcbxd_exec_t","cgdcbxd_t","cgdcbxd_unit_file_t","cgdcbxd_var_run_t","ganesha_use_fusefs","ganesha_exec_t","ganesha_t","ganesha_tmp_t","ganesha_unit_file_t","ganesha_var_log_t","ganesha_var_run_t","ganesha_use_fusefs"]

# types, attributes and boolean contained in container-selinux
CONTAINER_TYPES=["container_connect_any","container_runtime_t","container_runtime_exec_t","spc_t","container_auth_t","container_auth_exec_t","spc_var_run_t","container_var_lib_t","container_home_t","container_config_t","container_lock_t","container_log_t","container_runtime_tmp_t","container_runtime_tmpfs_t","container_var_run_t","container_plugin_var_run_t","container_unit_file_t","container_devpts_t","container_share_t","container_port_t","container_build_t","container_logreader_t","docker_log_t","docker_tmpfs_t","docker_share_t","docker_t","docker_lock_t","docker_home_t","docker_exec_t","docker_unit_file_t","docker_devpts_t","docker_config_t","docker_tmp_t","docker_auth_exec_t","docker_plugin_var_run_t","docker_port_t","docker_auth_t","docker_var_run_t","docker_var_lib_t","container_domain","container_net_domain"]


class SELinuxContentScanner(Actor):
    '''
    Scan the system for any SELinux customizations

    Find SELinux policy customizations (custom policy modules and changes
    introduced by semanage) and save them in SELinuxModules and SELinuxCustom
    models. Customizations that are incompatible with SELinux policy on RHEL-8
    are removed.
    '''
    name = 'selinuxcontentscanner'
    consumes = (SELinuxFacts,)
    produces = (SELinuxModules, SELinuxCustom, SELinuxRequestRPMs, RpmTransactionTasks)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        # exit if SELinux is disabled
        for fact in self.consume(SELinuxFacts):
            if not fact.enabled:
                return

        (semodule_list, rpms_to_keep, rpms_to_install) = self.getSELinuxModules()

        self.produce(SELinuxModules(modules=semodule_list))
        self.produce(
            RpmTransactionTasks(
                to_install = rpms_to_install,
                # possibly not necessary - dnf should not remove RPMs (that exist in both RHEL 7 and 8) durign update
                to_keep = rpms_to_keep
            )
        )
        # this is produced so that we can later verify that the RPMs are present after upgrade
        self.produce(
            SELinuxRequestRPMs(
                to_install = rpms_to_install,
                to_keep = rpms_to_keep
            )
        )

        semanage_removed = []
        semanage_valid = []
        try:
            # Collect SELinux customizations and select the ones that
            # can be reapplied after the upgrade
            semanage = run(['semanage', 'export'], split=True)
            for line in semanage.get("stdout", []):
                for setype in REMOVED_TYPES_:
                    if setype in line:
                        semanage_removed.append(line)
                        break
                else:
                    semanage_valid.append(line)

        except CalledProcessError as e:
            self.log.info("Failed to export SELinux customizations: %s", str(e))
            return

        self.produce(
            SELinuxCustom(
                commands=semanage_valid,
                removed=semanage_removed
            )
        )

    def checkModule(self, name):
        '''
        Check if given module contains one of removed types.

        If so, comment out corresponding lines and return them.
        The function expects a text file "$name" containing cil policy
        to be present in the current directory.
        '''
        try:
            removed = run(['grep', '-w', '-E', "|".join(REMOVED_TYPES_), name], split=True)
            run(['sed', '-i', '/%s/s/^/;/g' % '\|'.join(REMOVED_TYPES_), name])
            return removed.get("stdout", [])
        except CalledProcessError:
            return []


    def listSELinuxModules(self):
        '''
        Produce list of SELinux policy modules

        Returns list of tuples (name,priority)
        '''
        try:
            semodule = run(['semodule', '-lfull'], split=True)
        except CalledProcessError:
            return []

        modules = []
        for module in semodule.get("stdout", []):
            # Matching line such as "100 zebra             pp "
            # "<priority> <module name>    <module type - pp/cil> "
            m = re.match(r'([0-9]+)\s+([\w-]+)\s+([\w-]+)\s*\Z', module)
            if not m:
                #invalid output of "semodule -lfull"
                self.log.info('Invalid output of "semodule -lfull": %s', module)
                continue
            modules.append((m.group(2), m.group(1)))

        return modules


    def getSELinuxModules(self):
        '''
        Read all custom SELinux policy modules from the system

        Returns 3-tuple (modules, retain_rpms, install_rpms)
        where "modules" is a list of "SELinuxModule" objects,
        "retain_rpms" is a list of RPMs that should be retained 
        during the upgrade and "install_rpms" is a list of RPMs
        that should be installed during the upgrade

        '''

        modules = self.listSELinuxModules()
        semodule_list = []
        # list of rpms containing policy modules to be installed on RHEL 8
        retain_rpms = []
        install_rpms = []

        # modules need to be extracted into cil files
        # cd to /tmp/selinux and save working directory so that we can return there

        # clear working directory
        rmtree(WORKING_DIRECTORY, ignore_errors=True)

        try:
            wd = os.getcwd()
            os.mkdir(WORKING_DIRECTORY)
            os.chdir(WORKING_DIRECTORY)
        except OSError:
            self.log.info("Failed to access working directory! Aborting.")
            return ([],[],[])

        for (name, priority) in modules:
            if priority == "200":
                # Module on priority 200 was installed by an RPM
                # Request $name-selinux to be installed on RHEL8
                retain_rpms.append(name + "-selinux")
                continue
            if priority == "100":
                # module from selinux-policy-* package - skipping
                continue
            # extract custom module and save it to SELinuxModule object
            try:
                run(['semodule', '-c', '-X', priority, '-E', name])
                # check if the module contains invalid types and remove them if so
                removed = self.checkModule(name + ".cil")

                # get content of the module
                try:
                    with open(name + ".cil", 'r') as cil_file:
                        module_content = cil_file.read()
                except OSError as e:
                    self.log.info("Error reading %s.cil : %s", name, str(e))
                    continue

                semodule_list.append(SELinuxModule(
                    name=name,
                    priority=int(priority),
                    content=module_content,
                    removed=removed
                    )
                )
            except CalledProcessError:
                self.log.info("Module %s could not be extracted!", name)
                continue
            # rename the cil module file so that it does not clash
            # with the same module on different priority
            try:
                os.rename(name + ".cil",  "%s_%s" % (name, priority))
            except OSError:
                # TODO leapp.libraries.stdlib.api.current_logger()
                # and move the method to a library
                self.log.info("Failed to rename module file.")
        # this is necessary for check if container-selinux needs to be installed
        try:
            run(['semanage', 'export', '-f', 'semanage'])
        except CalledProcessError:
            pass
        # Check if modules contain any type, attribute, or boolean contained in container-selinux and install it if so
        # This is necessary since container policy module is part of selinux-policy-targeted in RHEL 7 (but not in RHEL 8)
        try:
            semodule = run(['grep', '-w', '-r', '-E', "|".join(CONTAINER_TYPES)], split=False)
            # Request "container-selinux" to be installed since container types where used in local customizations
            # and container-selinux policy was removed from selinux-policy-* packages
            install_rpms.append("container-selinux")
        except CalledProcessError:
            # expected, ignore exception
            pass

        try:
            os.chdir(wd)
        except OSError:
            pass
        rmtree(WORKING_DIRECTORY, ignore_errors=True)

        return (semodule_list, retain_rpms, install_rpms)
