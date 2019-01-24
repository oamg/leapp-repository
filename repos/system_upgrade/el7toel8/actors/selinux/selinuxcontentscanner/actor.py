from leapp.actors import Actor
from leapp.models import SELinuxModules, SELinuxModule, SELinuxCustom, SystemFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import call
import subprocess
import re
import os
from shutil import rmtree

WORKING_DIRECTORY = '/tmp/selinux/'

# types and attributes that where removed between RHEL 7 and 8
REMOVED_TYPES_=["base_typeattr_15","direct_run_init","gpgdomain","httpd_exec_scripts","httpd_user_script_exec_type","ibendport_type","ibpkey_type","pcmcia_typeattr_2","pcmcia_typeattr_3","pcmcia_typeattr_4","pcmcia_typeattr_5","pcmcia_typeattr_6","pcmcia_typeattr_7","sandbox_caps_domain","sandbox_typeattr_2","sandbox_typeattr_3","sandbox_typeattr_4","server_ptynode","systemctl_domain","user_home_content_type","userhelper_type","cgdcbxd_exec_t","cgdcbxd_t","cgdcbxd_unit_file_t","cgdcbxd_var_run_t","ganesha_use_fusefs","ganesha_exec_t","ganesha_t","ganesha_tmp_t","ganesha_unit_file_t","ganesha_var_log_t","ganesha_var_run_t","ganesha_use_fusefs"]
# to be used with grep
REMOVED_TYPES="|".join(REMOVED_TYPES_)
# to be used with sed
SED_COMMAND='/' + '\|'.join(REMOVED_TYPES_) + '/s/^/;/g'

# types, attributes and boolean contained in container-selinux
CONTAINER_TYPES="|".join(["container_connect_any","container_runtime_t","container_runtime_exec_t","spc_t","container_auth_t","container_auth_exec_t","spc_var_run_t","container_var_lib_t","container_home_t","container_config_t","container_lock_t","container_log_t","container_runtime_tmp_t","container_runtime_tmpfs_t","container_var_run_t","container_plugin_var_run_t","container_unit_file_t","container_devpts_t","container_share_t","container_port_t","container_build_t","container_logreader_t","docker_log_t","docker_tmpfs_t","docker_share_t","docker_t","docker_lock_t","docker_home_t","docker_exec_t","docker_unit_file_t","docker_devpts_t","docker_config_t","docker_tmp_t","docker_auth_exec_t","docker_plugin_var_run_t","docker_port_t","docker_auth_t","docker_var_run_t","docker_var_lib_t","container_domain","container_net_domain"])


class SELinuxContentScanner(Actor):
    name = 'selinuxcontentscanner'
    description = 'No description has been provided for the selinuxcontentscanner actor.'
    consumes = (SystemFacts, )
    produces = (SELinuxModules, SELinuxCustom, )
    tags = (FactsPhaseTag, IPUWorkflowTag, )

    def process(self):
        # exit if SELinux is disabled
        for fact in self.consume(SystemFacts):
            if fact.selinux.enabled is False:
                return

        semodule_list = self.getSELinuxModules()

        self.produce(SELinuxModules(modules=semodule_list))

        semanage_removed = []
        semanage_valid = []
        try:
            # Collect SELinux customizations and select the ones that
            # can be reapplied after the upgrade
            semanage = call(['semanage', 'export'], split=True)
            for line in semanage:
                for setype in REMOVED_TYPES_:
                    if setype in line:
                        semanage_removed.append(line)
                        break
                else:
                    semanage_valid.append(line)

        except subprocess.CalledProcessError:
            return

        self.produce(
            SELinuxCustom(
                commands=semanage_valid,
                removed=semanage_removed
            )
        )

        #cmd = [ 'semanage', 'export' ]
        #stdout = call(cmd, split=False)
        #semodules = SELinuxModules(
        #    modules=[SELinuxModule(
        #        name="nn",
        #        priority=1,
        #        content=stdout
        #)],)
        #self.produce(semodules)



    def checkModule(self, name):
        """ Check if module contains one of removed types.
            If so, comment out corresponding lines and return them.
        """
        try:
            removed = call(['grep', '-w', '-E', REMOVED_TYPES, name], split=True)
            call(['sed', '-i', SED_COMMAND, name])
            return removed
        except subprocess.CalledProcessError:
            return []

    def parseSemodule(self, modules_str):
        """Parse list of modules into list of tuples (name,priority)"""
        modules = []
        for module in modules_str:
            # Matching line such as "100 zebra             pp "
            # "<priority> <module name>    <module type - pp/cil> "
            m = re.match('([0-9]+)\s+(\w+)\s+(\w+)\s*\Z', module)
            if not m:
                #invalid output of "semodule -lfull"
                break
            modules.append((m.group(2), m.group(1)))

        return modules

    def getSELinuxModules(self):
        try:
            semodule = call(['semodule', '-lfull'], split=True)
        except subprocess.CalledProcessError:
            return

        modules = self.parseSemodule(semodule)
        semodule_list = []

        # modules need to be extracted into cil files
        # cd to /tmp/selinux and save working directory so that we can return there
        try:
            # clear working directory
            rmtree(WORKING_DIRECTORY)
        except OSError:
            #expected
            pass
        try:
            wd = os.getcwd()
            os.mkdir(WORKING_DIRECTORY)
            os.chdir(WORKING_DIRECTORY)
        except OSError:
            self.log.info("Failed to access working directory! Aborting.")
            return []

        for (name, priority) in modules:
            if priority == "200":
                #TODO - request "name-selinux" to be installed
                continue
            if priority == "100":
                #module from selinux-policy-* package - skipping
                continue
            # extract custom module and save it to SELinuxModule object
            try:
                call(['semodule', '-c', '-X', priority, '-E', name])
                # check if the module contains invalid types and remove them if so
                removed = self.checkModule(name + ".cil")
                # get content of the module
                module_content = call(['cat', name + ".cil"], split=False)

                semodule_list.append(SELinuxModule(
                    name=name,
                    priority=int(priority),
                    content=module_content,
                    removed=removed
                    )
                )
            except subprocess.CalledProcessError:
                continue
            # rename the cil module file so that it does not clash
            # with the same module on different priority
            try:
                os.rename(name + ".cil", name + "_" + str(priority))
            except OSError:
                self.log.info("Failed to rename module file.")
        # this is necessary for check if container-selinux needs to be installed
        try:
            call(['semanage', 'export', '-f', 'semanage'])
        except subprocess.CalledProcessError:
            pass
        # Check if modules contain any type, attribute, or boolean contained in container-selinux and install it if so
        # This is necessary since container policy module is part of selinux-policy-targeted in RHEL 7 (but not in RHEL 8)
        try:
            semodule = call(['grep', '-w', '-r', '-E', CONTAINER_TYPES], split=False)
            #TODO - request "container-selinux" to be installed
        except subprocess.CalledProcessError:
            # expected, ignore exception
            pass

        try:
            rmtree(WORKING_DIRECTORY)
            os.chdir(wd)
        except OSError:
            pass

        return semodule_list
