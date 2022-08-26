import errno
import functools
import grp
import logging
import os
import pwd
import re

import six

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import (
    ActiveKernelModule,
    ActiveKernelModulesFacts,
    DefaultGrub,
    DefaultGrubInfo,
    FirewallsFacts,
    FirewallStatus,
    FirmwareFacts,
    Group,
    GroupsFacts,
    GrubCfgBios,
    KernelModuleParameter,
    RepositoriesFacts,
    SELinuxFacts,
    SysctlVariable,
    SysctlVariablesFacts,
    User,
    UsersFacts
)


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def anyendswith(value, ends):
    """ Check if `value` ends with one of the possible `ends` """
    for end in ends:
        if value.endswith(end):
            return True
    return False


def anyhasprefix(value, prefixes):
    """ Check if `value` starts with on of the possible `prefixes` """
    for p in prefixes:
        if value.startswith(p):
            return True
    return False


@aslist
def _get_system_users():
    skipped_user_names = []
    for p in pwd.getpwall():
        # The /etc/passwd can contain special entries from another service source such as NIS or LDAP. These entries
        # start with + or - sign and might not contain all the mandatory fields, thus are skipped along with other
        # invalid entries for now. The UID and GID fields are always defined by pwd to 0 even when not specifiead in
        # /etc/passwd.
        if p.pw_name != '' and not p.pw_name.startswith(('+', '-')) and p.pw_dir:
            yield User(
                name=p.pw_name,
                uid=p.pw_uid,
                gid=p.pw_gid,
                home=p.pw_dir
            )
        else:
            skipped_user_names.append(p.pw_name)

    if skipped_user_names:
        api.current_logger().debug("These users from /etc/passwd that are special entries for service "
                                   "like NIS, or don't contain all mandatory fields won't be included "
                                   "in UsersFacts: {}".format(skipped_user_names))


def get_system_users_status():
    """ Get a list of users from `/etc/passwd` """
    return UsersFacts(users=_get_system_users())


@aslist
def _get_system_groups():
    skipped_group_names = []
    for g in grp.getgrall():
        # The /etc/group can contain special entries from another service source such as NIS or LDAP. These entries
        # start with + or - sign and might not contain all the mandatory fields, thus are skipped along with other
        # invalid entries for now. The GID field is always defined by pwd to 0 even when not specifiead in
        # /etc/group.
        if g.gr_name != '' and not g.gr_name.startswith(('+', '-')):
            yield Group(
                name=g.gr_name,
                gid=g.gr_gid,
                members=g.gr_mem
            )
        else:
            skipped_group_names.append(g.gr_name)

    if skipped_group_names:
        api.current_logger().debug("These groups from /etc/group that are special entries for service "
                                   "like NIS, or don't contain all mandatory fields won't be included "
                                   "in GroupsFacts: {}".format(skipped_group_names))


def get_system_groups_status():
    """ Get a list of groups from `/etc/groups` """
    return GroupsFacts(groups=_get_system_groups())


@aslist
def _get_active_kernel_modules(logger):
    lines = run(['lsmod'], split=True)['stdout']
    for l in lines[1:]:
        name = l.split(' ')[0]

        # Read parameters of the given module as exposed by the
        # `/sys` VFS, if there are no parameters exposed we just
        # take the name of the module
        base_path = '/sys/module/{module}'.format(module=name)
        parameters_path = os.path.join(base_path, 'parameters')
        if not os.path.exists(parameters_path):
            yield ActiveKernelModule(filename=name, parameters=[])
            continue

        # Use `modinfo` to probe for signature information
        parameter_dict = {}
        try:
            signature = run(['modinfo', '-F', 'signature', name], split=False)['stdout']
        except CalledProcessError:
            signature = None

        signature_string = None
        if signature:
            # Remove whitespace from the signature string
            signature_string = re.sub(r"\s+", "", signature, flags=re.UNICODE)

        # Since we're using the `/sys` VFS we need to use `os.listdir()` to get
        # all the property names and then just read from all the listed paths
        parameters = sorted(os.listdir(parameters_path))
        for param in parameters:
            try:
                with open(os.path.join(parameters_path, param), mode='r') as fp:
                    parameter_dict[param] = fp.read().strip()
            except IOError as exc:
                # Some parameters are write-only, in that case we just log the name of parameter
                # and the module and continue
                if exc.errno in (errno.EACCES, errno.EPERM):
                    msg = 'Unable to read parameter "{param}" of kernel module "{name}"'
                    logger.warning(msg.format(param=param, name=name))
                else:
                    raise exc

        # Project the dictionary as a list of key values
        items = [
            KernelModuleParameter(name=k, value=v)
            for (k, v) in six.iteritems(parameter_dict)
        ]

        yield ActiveKernelModule(
            filename=name,
            parameters=items,
            signature=signature_string
        )


def get_active_kernel_modules_status(logger):
    """ Get a list of active kernel modules """
    return ActiveKernelModulesFacts(kernel_modules=_get_active_kernel_modules(logger))


@aslist
def _get_sysctls():
    unstable = ('fs.dentry-state', 'fs.file-nr', 'fs.inode-nr',
                'fs.inode-state', 'kernel.random.uuid', 'kernel.random.entropy_avail',
                'kernel.ns_last_pid', 'net.netfilter.nf_conntrack_count',
                'net.netfilter.nf_conntrack_events', 'kernel.sched_domain.',
                'dev.cdrom.info', 'kernel.pty.nr')

    variables = []
    for sc in run(['sysctl', '-a'], split=True)['stdout']:
        name = sc.split(' ', 1)[0]
        # if the sysctl name has an unstable prefix, we skip
        if anyhasprefix(name, unstable):
            continue
        variables.append(sc)

    # sort our variables so they can be diffed directly when needed
    for var in sorted(variables):
        name, value = tuple(map(type(var).strip, var.split('=', 1)))
        yield SysctlVariable(
            name=name,
            value=value
        )


def get_sysctls_status():
    r""" Get a list of stable `sysctls` variables

        Note that some variables are inherently unstable and we need to blacklist
        them:

        diff -u <(sysctl -a 2>/dev/null | sort) <(sysctl -a 2>/dev/null | sort)\
                | grep -E '^\+[a-z]'\
                | cut -d' ' -f1\
                | cut -d+ -f2
    """
    return SysctlVariablesFacts(sysctl_variables=_get_sysctls())


def get_repositories_status():
    """ Get a basic information about YUM repositories installed in the system """
    return RepositoriesFacts(repositories=repofileutils.get_parsed_repofiles())


def get_selinux_status():
    """ Get SELinux status information """
    # will be None if something went wrong or contain SELinuxFacts otherwise
    res = None
    try:
        import selinux  # pylint: disable=import-outside-toplevel
    except ImportError:
        api.report_error("SELinux Import Error", details="libselinux-python package must be installed.")
        return res

    outdata = dict({'enabled': selinux.is_selinux_enabled() == 1})
    outdata['mls_enabled'] = selinux.is_selinux_mls_enabled() == 1

    try:
        outdata['runtime_mode'] = "enforcing" if selinux.security_getenforce() == 1 else "permissive"
        # FIXME: check selinux_getenforcemode[0] (that should be return value of a underneath function)
        enforce_mode = selinux.selinux_getenforcemode()[1]
        if enforce_mode >= 0:
            outdata['static_mode'] = "enforcing" if enforce_mode == 1 else "permissive"
        else:
            outdata['static_mode'] = "disabled"
        outdata['policy'] = selinux.selinux_getpolicytype()[1]
    except OSError:
        # This happens when SELinux is disabled
        # [Errno 2] No such file or directory
        outdata['runtime_mode'] = 'permissive'
        outdata['static_mode'] = 'disabled'
        outdata['policy'] = 'targeted'

    res = SELinuxFacts(**outdata)
    return res


def get_firewalls_status():
    """ Get firewalld status information """
    logger = logging.getLogger('get_firewalld_status')

    def _get_firewall_status(service_name):
        try:
            ret_list = run(['systemctl', 'is-active', service_name], split=True)['stdout']
            active = ret_list[0] == 'active'
        except CalledProcessError:
            active = False
            logger.debug('The %s service is likely not active', service_name)

        try:
            ret_list = run(['systemctl', 'is-enabled', service_name], split=True)['stdout']
            enabled = ret_list[0] == 'enabled'
        except CalledProcessError:
            enabled = False
            logger.debug('The %s service is likely not enabled nor running', service_name)

        return FirewallStatus(
            active=active,
            enabled=enabled,
        )

    return FirewallsFacts(
        firewalld=_get_firewall_status('firewalld'),
        iptables=_get_firewall_status('iptables'),
        ip6tables=_get_firewall_status('ip6tables'),
    )


def get_firmware():
    firmware = 'efi' if os.path.isdir('/sys/firmware/efi') else 'bios'
    if architecture.matches_architecture(architecture.ARCH_PPC64LE):
        ppc64le_opal = bool(os.path.isdir('/sys/firmware/opal/'))
        return FirmwareFacts(firmware=firmware, ppc64le_opal=ppc64le_opal)
    return FirmwareFacts(firmware=firmware)


@aslist
def _default_grub_info():
    default_grb_fpath = '/etc/default/grub'
    if not os.path.isfile(default_grb_fpath):
        reporting.create_report([
            reporting.Title('File "{}" does not exist!'.format(default_grb_fpath)),
            reporting.Summary(
                'Leapp detected "{}" does not exist. The file is essential for the in-place upgrade '
                'to finish successfully. This scenario might have occurred if the system was already '
                'upgraded from RHEL 6. Please re-create the file manually.'.format(default_grb_fpath)
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.RelatedResource('file', default_grb_fpath),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/3185891',
                title='How to re-create the missing "{}" file in Red Hat Enterprise Linux 7?'.format(
                    default_grb_fpath
                )
            ),
        ])
    else:
        for line in run(['cat', default_grb_fpath], split=True)['stdout']:
            line = line.strip()
            if not line or line[0] == '#':
                # skip comments and empty lines
                continue
            try:
                name, value = tuple(map(type(line).strip, line.split('=', 1)))
            except ValueError as e:
                # we do not want to really continue when we cannot parse this file
                # TODO(pstodulk): rewrite this in the form we produce inhibitor
                # with problematic lines. This is improvement just in comparison
                # to the original hard crash.
                raise StopActorExecutionError(
                    'Failed parsing of {}'.format(default_grb_fpath),
                    details={
                        'error': str(e),
                        'problematic line': str(line)
                    }
                )

            yield DefaultGrub(
                name=name,
                value=value
            )


def get_default_grub_conf():
    """ Get a list of GRUB parameters from /etc/default/grub """
    return DefaultGrubInfo(default_grub_info=_default_grub_info())


def get_bios_grubcfg_details():
    """ Get BIOS (non-EFI) Grub config details """
    if get_firmware().firmware == 'bios' and not architecture.matches_architecture(architecture.ARCH_S390X):
        with open('/boot/grub2/grub.cfg') as fo:
            content = fo.read()
        insmod_bls = bool('insmod blscfg' in content)
        return GrubCfgBios(insmod_bls=insmod_bls)
    return None
