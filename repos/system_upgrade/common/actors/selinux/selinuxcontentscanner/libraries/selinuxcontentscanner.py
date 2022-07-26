import os
import re
from shutil import rmtree

from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SELinuxModule

# types and attributes that where removed between RHEL 7 and 8
REMOVED_TYPES_EL7 = ["base_typeattr_15", "direct_run_init", "gpgdomain", "httpd_exec_scripts",
                     "httpd_user_script_exec_type", "ibendport_type", "ibpkey_type", "pcmcia_typeattr_2",
                     "pcmcia_typeattr_3", "pcmcia_typeattr_4", "pcmcia_typeattr_5", "pcmcia_typeattr_6",
                     "pcmcia_typeattr_7", "sandbox_caps_domain", "sandbox_typeattr_2", "sandbox_typeattr_3",
                     "sandbox_typeattr_4", "server_ptynode", "systemctl_domain", "user_home_content_type",
                     "userhelper_type", "cgdcbxd_exec_t", "cgdcbxd_t", "cgdcbxd_unit_file_t", "cgdcbxd_var_run_t",
                     "ganesha_use_fusefs", "ganesha_exec_t", "ganesha_t", "ganesha_tmp_t", "ganesha_unit_file_t",
                     "ganesha_var_log_t", "ganesha_var_run_t", "ganesha_use_fusefs"]

# types and attributes that where removed between RHEL 8 and 9
REMOVED_TYPES_EL8 = ["cephfs_t", "cgdcbxd_exec_t", "cgdcbxd_t", "cgdcbxd_unit_file_t", "cgdcbxd_var_run_t",
                     "cloud_what_var_cache_t", "journal_remote_client_packet_t", "journal_remote_port_t",
                     "journal_remote_server_packet_t", "kdbusfs_t", "logging_syslogd_list_non_security_dirs",
                     "nvme_device_t", "pcp_pmmgr_exec_t", "pcp_pmmgr_initrc_exec_t", "pcp_pmmgr_t",
                     "pcp_pmwebd_exec_t", "pcp_pmwebd_initrc_exec_t", "pcp_pmwebd_t", "rpm_transition_domain",
                     "systemd_journal_upload_exec_t", "systemd_journal_upload_t",
                     "systemd_journal_upload_var_lib_t", "virt_qmf_exec_t", "virt_qmf_t"]

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

WORKING_DIRECTORY = "/tmp/selinux/"

# list of policy modules used by udica
UDICA_TEMPLATES = {"base_container", "config_container", "home_container", "log_container",
                   "net_container", "tmp_container", "tty_container", "virt_container", "x_container"}


def check_module(name):
    """
    Check if given module contains one of removed types and comment out corresponding lines.

    The function expects a text file "$name" containing cil policy
    to be present in the current directory.

    Returns a list of invalid lines.
    """
    # get removed_types list based on upgrade path
    removed_types = REMOVED_TYPES_EL7 if version.get_source_major_version() == "7" else REMOVED_TYPES_EL8

    try:
        removed = run(["grep", "-w", "-E", "|".join(removed_types), name], split=True)
        # Add ";" at the beginning of invalid lines (comment them out)
        run(["sed", "-i", "/{}/s/^/;/g".format(r"\|".join(removed_types)), name])
        return removed.get("stdout", [])
    except CalledProcessError:
        return []


def list_selinux_modules():
    """
    Produce list of SELinux policy modules

    Returns list of tuples (name,priority)
    """
    try:
        semodule = run(['semodule', '-lfull'], split=True)
    except CalledProcessError as e:
        api.current_logger().warning('Cannot get list of selinux modules: {}'.format(e))
        return []

    modules = []
    for module in semodule.get("stdout", []):
        # Matching line such as "100 zebra             pp "
        # "<priority> <module name>    <module type - pp/cil> "
        m = re.match(r'([0-9]+)\s+([\w-]+)\s+([\w-]+)\s*\Z', module)
        if not m:
            # invalid output of "semodule -lfull"
            api.current_logger().warning('Invalid output of "semodule -lfull": {}'.format(module))
            continue
        modules.append((m.group(2), m.group(1)))

    return modules


def get_selinux_modules():
    """
    Read all custom SELinux policy modules from the system

    Returns a tuple (modules, install_rpms)
    where "modules" is a list of "SELinuxModule" objects
    and "install_rpms" is a list of RPMs
    that should be installed during the upgrade

    """

    modules = list_selinux_modules()
    # custom selinux policy modules
    semodule_list = []
    # udica templates
    template_list = []
    # list of rpms containing policy modules to be installed on RHEL 8
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
        # Udica templates should not be transfered, we only need a list of their
        # names and priorities so that we can reinstall their latest verisions
        if name in UDICA_TEMPLATES:
            template_list.append(
                SELinuxModule(
                    name=name,
                    priority=int(priority),
                    content='',
                    removed=[],
                )
            )
            continue

        if priority in ["100", "200"]:
            # 100 - module from selinux-policy-* package
            # 200 - DSP module - installed by an RPM - handled by PES
            continue
        # extract custom module and save it to SELinuxModule object
        module_file = name + ".cil"
        try:
            run(["semodule", "-c", "-X", priority, "-E", name])
            # check if the module contains invalid types and remove them if so
            removed = check_module(module_file)

            # get content of the module
            try:
                with open(module_file) as cil_file:
                    module_content = cil_file.read()
            except OSError as e:
                api.current_logger().warning("Error reading {}.cil : {}".format(name, e))
                continue

            semodule_list.append(
                SELinuxModule(
                    name=name,
                    priority=int(priority),
                    content=module_content,
                    removed=removed,
                )
            )
        except CalledProcessError:
            api.current_logger().warning("Module {} could not be extracted!".format(name))
            continue
        # rename the cil module file so that it does not clash
        # with the same module on different priority
        try:
            os.rename(module_file, "{}_{}".format(name, priority))
        except OSError:
            api.current_logger().warning(
                "Failed to rename module file {} to include priority.".format(name)
            )

    # Udica templates where moved to container-selinux package.
    # Make sure it is installed so that the templates can be reinstalled
    if template_list:
        install_rpms.append("container-selinux")

    # Process customizations introduced by "semanage"
    # this is necessary for check if container-selinux needs to be installed
    try:
        run(["semanage", "export", "-f", "semanage"])
    except CalledProcessError:
        pass
    # Check if modules contain any type, attribute, or boolean contained in container-selinux and install it if so
    # This is necessary since container policy module is part of selinux-policy-targeted in RHEL 7 (but not in RHEL 8)
    try:
        run(["grep", "-w", "-r", "-E", "|".join(CONTAINER_TYPES)], split=False)
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

    return (semodule_list, template_list, list(set(install_rpms)))


def get_selinux_customizations():
    """
    Extract local SELinux customizations introduced by semanage command

    Returns tuple (semanage_valid, semanage_removed)
    where "semanage_valid" is a list of semanage commands
    which should be safe to re-apply on RHEL 8 system
    and "semanage_removed" is a list of commands that
    will no longer be valid after system upgrade
    """
    removed_types = REMOVED_TYPES_EL7 if version.get_source_major_version() == "7" else REMOVED_TYPES_EL8

    semanage_removed = []
    semanage_valid = []
    try:
        # Collect SELinux customizations and select the ones that
        # can be reapplied after the upgrade
        semanage = run(["semanage", "export"], split=True)
        for line in semanage.get("stdout", []):
            # Skip "deleteall" commands to avoid removing customizations
            # done by package scripts during upgrade
            if " -D" in line:
                continue
            for setype in removed_types:
                if setype in line:
                    semanage_removed.append(line)
                    break
            else:
                semanage_valid.append(line)

    except CalledProcessError as e:
        api.current_logger().warning(
            "Failed to export SELinux customizations: {}".format(e.stderr)
        )

    return (semanage_valid, semanage_removed)
