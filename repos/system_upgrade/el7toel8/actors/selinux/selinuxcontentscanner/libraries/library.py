import os
import re
from shutil import rmtree

from leapp.libraries.stdlib import api, run, CalledProcessError
from leapp.models import SELinuxModule

# types and attributes that where removed between RHEL 7 and 8
REMOVED_TYPES_ = ["base_typeattr_15", "direct_run_init", "gpgdomain", "httpd_exec_scripts",
                  "httpd_user_script_exec_type", "ibendport_type", "ibpkey_type", "pcmcia_typeattr_2",
                  "pcmcia_typeattr_3", "pcmcia_typeattr_4", "pcmcia_typeattr_5", "pcmcia_typeattr_6",
                  "pcmcia_typeattr_7", "sandbox_caps_domain", "sandbox_typeattr_2", "sandbox_typeattr_3",
                  "sandbox_typeattr_4", "server_ptynode", "systemctl_domain", "user_home_content_type",
                  "userhelper_type", "cgdcbxd_exec_t", "cgdcbxd_t", "cgdcbxd_unit_file_t", "cgdcbxd_var_run_t",
                  "ganesha_use_fusefs", "ganesha_exec_t", "ganesha_t", "ganesha_tmp_t", "ganesha_unit_file_t",
                  "ganesha_var_log_t", "ganesha_var_run_t", "ganesha_use_fusefs"]

# types, attributes and boolean contained in container-selinux
CONTAINER_TYPES = ["container_connect_any", "container_runtime_t", "container_runtime_exec_t", "spc_t",
                   "container_auth_t", "container_auth_exec_t", "spc_var_run_t", "container_var_lib_t",
                   "container_home_t", "container_config_t", "container_lock_t", "container_log_t",
                   "container_runtime_tmp_t", "container_runtime_tmpfs_t", "container_var_run_t",
                   "container_plugin_var_run_t", "container_unit_file_t", "container_devpts_t", "container_share_t",
                   "container_port_t", "container_build_t", "container_logreader_t", "docker_log_t", "docker_tmpfs_t",
                   "docker_share_t", "docker_t", "docker_lock_t", "docker_home_t", "docker_exec_t",
                   "docker_unit_file_t", "docker_devpts_t", "docker_config_t", "docker_tmp_t", "docker_auth_exec_t",
                   "docker_plugin_var_run_t", "docker_port_t", "docker_auth_t", "docker_var_run_t",
                   "docker_var_lib_t", "container_domain", "container_net_domain"]

WORKING_DIRECTORY = '/tmp/selinux/'


def check_module(name):
    '''
    Check if given module contains one of removed types and comment out corresponding lines.

    The function expects a text file "$name" containing cil policy
    to be present in the current directory.

    Returns a list of invalid lines.
    '''
    try:
        removed = run(['grep', '-w', '-E', "|".join(REMOVED_TYPES_), name], split=True)
        # Add ";" at the beginning of invalid lines (comment them out)
        run(['sed', '-i', '/{}/s/^/;/g'.format(r'\|'.join(REMOVED_TYPES_)), name])
        return removed.get("stdout", [])
    except CalledProcessError:
        return []


def list_selinux_modules():
    '''
    Produce list of SELinux policy modules

    Returns list of tuples (name,priority)
    '''
    try:
        semodule = run(['semodule', '-lfull'], split=True)
    except CalledProcessError:
        api.current_logger().warning('Cannot get list of selinux modules')
        return []

    modules = []
    for module in semodule.get("stdout", []):
        # Matching line such as "100 zebra             pp "
        # "<priority> <module name>    <module type - pp/cil> "
        m = re.match(r'([0-9]+)\s+([\w-]+)\s+([\w-]+)\s*\Z', module)
        if not m:
            # invalid output of "semodule -lfull"
            api.current_logger().warning('Invalid output of "semodule -lfull": %s', module)
            continue
        modules.append((m.group(2), m.group(1)))

    return modules


def get_selinux_modules():
    '''
    Read all custom SELinux policy modules from the system

    Returns 3-tuple (modules, retain_rpms, install_rpms)
    where "modules" is a list of "SELinuxModule" objects,
    "retain_rpms" is a list of RPMs that should be retained
    during the upgrade and "install_rpms" is a list of RPMs
    that should be installed during the upgrade

    '''

    modules = list_selinux_modules()
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
        api.current_logger().warning("Failed to access working directory! Aborting.")
        return ([], [], [])

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
        module_file = name + ".cil"
        try:
            run(['semodule', '-c', '-X', priority, '-E', name])
            # check if the module contains invalid types and remove them if so
            removed = check_module(module_file)

            # get content of the module
            try:
                with open(module_file, 'r') as cil_file:
                    module_content = cil_file.read()
            except OSError as e:
                api.current_logger().warning("Error reading %s.cil : %s", name, str(e))
                continue

            semodule_list.append(SELinuxModule(
                name=name,
                priority=int(priority),
                content=module_content,
                removed=removed
                )
            )
        except CalledProcessError:
            api.current_logger().warning("Module %s could not be extracted!", name)
            continue
        # rename the cil module file so that it does not clash
        # with the same module on different priority
        try:
            os.rename(module_file, "{}_{}".format(name, priority))
        except OSError:
            api.current_logger().warning("Failed to rename module file %s to include priority.", name)
    # this is necessary for check if container-selinux needs to be installed
    try:
        run(['semanage', 'export', '-f', 'semanage'])
    except CalledProcessError:
        pass
    # Check if modules contain any type, attribute, or boolean contained in container-selinux and install it if so
    # This is necessary since container policy module is part of selinux-policy-targeted in RHEL 7 (but not in RHEL 8)
    try:
        run(['grep', '-w', '-r', '-E', "|".join(CONTAINER_TYPES)], split=False)
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

    return (semodule_list, list(set(retain_rpms)), list(set(install_rpms)))


def get_selinux_customizations():
    '''
    Extract local SELinux customizations introduced by semanage command

    Returns tuple (semanage_valid, semanage_removed)
    where "semanage_valid" is a list of semanage commands
    which should be safe to re-apply on RHEL 8 system
    and "semanage_removed" is a list of commands that
    will no longer be valid after system upgrade
    '''

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
        api.current_logger().warning("Failed to export SELinux customizations: %s", str(e.stderr))

    return (semanage_valid, semanage_removed)
