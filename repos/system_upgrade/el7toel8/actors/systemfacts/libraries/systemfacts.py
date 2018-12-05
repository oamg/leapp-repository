import errno
import functools
import grp
import json
import os
import pwd
import re
import six
import subprocess
import logging
from subprocess import CalledProcessError
from leapp.libraries.stdlib import call


try:
    import ConfigParser as configparser
except ImportError:
    import configparser

from leapp.models import SysctlVariable, ActiveKernelModule, KernelModuleParameter, User, Group, Repositories,\
    RepositoryData, SELinux, fields, FirewallStatus, Firewalls


def aslist(f):
    ''' Decorator used to convert generator to list '''
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def anyendswith(value, ends):
    ''' Check if `value` ends with one of the possible `ends` '''
    for end in ends:
        if value.endswith(end):
            return True
    return False


def anyhasprefix(value, prefixes):
    ''' Check if `value` starts with on of the possible `prefixes` '''
    for p in prefixes:
        if value.startswith(p):
            return True
    return False


@aslist
def get_system_users():
    ''' Get a list of users from `/etc/passwd` '''
    for p in pwd.getpwall():
        yield User(
            name=p.pw_name,
            uid=p.pw_uid,
            gid=p.pw_gid,
            home=p.pw_dir
        )


@aslist
def get_system_groups():
    ''' Get a list of groups from `/etc/groups` '''
    for g in grp.getgrall():
        yield Group(
            name=g.gr_name,
            gid=g.gr_gid,
            members=g.gr_mem
        )


@aslist
def get_active_kernel_modules(logger):
    ''' Get a list of active kernel modules '''
    lines = call(['lsmod'])
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
            signature = call(['modinfo', '-F', 'signature', name], split=False)
        except subprocess.CalledProcessError:
            signature = None

        signature_string = None
        if signature:
            # Remove whitspace from the signature string
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


@aslist
def get_sysctls():
    r''' Get a list of stable `sysctls` variables

        Note that some variables are inherently unstable and we need to blacklist
        them:

        diff -u <(sysctl -a 2>/dev/null | sort) <(sysctl -a 2>/dev/null | sort)\
                | grep -E '^\+[a-z]'\
                | cut -d' ' -f1\
                | cut -d+ -f2
    '''

    unstable = ('fs.dentry-state', 'fs.file-nr', 'fs.inode-nr',
                'fs.inode-state', 'kernel.random.uuid', 'kernel.random.entropy_avail',
                'kernel.ns_last_pid', 'net.netfilter.nf_conntrack_count',
                'net.netfilter.nf_conntrack_events', 'kernel.sched_domain.',
                'dev.cdrom.info', 'kernel.pty.nr')

    variables = []
    for sc in call(['sysctl', '-a']):
        name = sc.split(' ', 1)[0]
        # if the sysctl name has an unstable prefix, we skip
        if anyhasprefix(name, unstable):
            continue
        variables.append(sc)

    # sort our variables so they can be diffed directly when needed
    for var in sorted(variables):
        name, value = tuple(map(type(var).strip, var.split('=')))
        yield SysctlVariable(
            name=name,
            value=value
        )


@aslist
def get_repositories():
    ''' Get a basic information about YUM repositories installed in the system '''
    def asbool(x):
        return x == 0

    @aslist
    def _parse(r):
        with open(r, mode='r') as fp:
            cp = configparser.ConfigParser()
            cp.readfp(fp)
            for section in cp.sections():
                prepared = {'additional_fields': {}}
                data = dict(cp.items(section))
                for key in data.keys():
                    if key in RepositoryData.fields:
                        if isinstance(RepositoryData.fields[key], fields.Boolean):
                            data[key] = asbool(data[key])
                        prepared[key] = data[key]
                    else:
                        prepared['additional_fields'][key] = data[key]
                prepared['additional_fields'] = json.dumps(prepared['additional_fields'])
                yield RepositoryData(**prepared)

    repos = call(
        ['find', '/etc/yum.repos.d/', '-type', 'f', '-name', '*.repo']
    )
    for repo in repos:
        yield Repositories(file=repo, data=_parse(repo))


def get_selinux_status():
    ''' Get SELinux status information '''
    def asbool(x):
        return x == 'enabled'

    def identity(x):
        return x

    key_mapping = (('SELinux status', 'enabled', asbool),
                   ('Policy MLS status', 'mls_enabled', asbool),
                   ('Loaded policy name', 'policy', identity),
                   ('Current mode', 'runtime_mode', identity),
                   ('Mode from config file', 'static_mode', identity),)

    outdata = {}
    for item in call(['sestatus']):
        for (key, mapped, cast) in key_mapping:
            if item.startswith(key):
                outdata[mapped] = cast(item[len(key)+1:].strip())

    return SELinux(**outdata)


def get_firewalls_status():
    ''' Get firewalld status information '''
    logger = logging.getLogger('get_firewalld_status')

    def _get_firewall_status(service_name):
        try:
            ret_list = call(['systemctl', 'is-active', service_name])
            active = ret_list[0] == 'active'
        except CalledProcessError:
            active = False
            logger.debug('The %s service is likely not active' % service_name)

        try:
            ret_list = call(['systemctl', 'is-enabled', service_name])
            enabled = ret_list[0] == 'enabled'
        except CalledProcessError:
            enabled = False
            logger.debug('The %s service is likely not enabled nor running' % service_name)

        return FirewallStatus(
                    active=active,
                    enabled=enabled,
                    )

    return Firewalls(
            firewalld=_get_firewall_status('firewalld'),
            iptables=_get_firewall_status('iptables'),
            )
