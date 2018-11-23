from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class User(Model):
    topic = SystemInfoTopic

    name = fields.String()
    uid = fields.Integer()
    gid = fields.Integer()
    home = fields.String()


class Group(Model):
    topic = SystemInfoTopic

    name = fields.String()
    gid = fields.Integer()
    members = fields.List(fields.String())


class RepositoryData(Model):
    topic = SystemInfoTopic

    name = fields.String()
    baseurl = fields.String()
    enabled = fields.Boolean(default=True)
    additional_fields = fields.Nullable(fields.String())


class Repositories(Model):
    topic = SystemInfoTopic

    file = fields.String()
    data = fields.List(fields.Model(RepositoryData))


class SysctlVariable(Model):
    topic = SystemInfoTopic

    name = fields.String()
    value = fields.String()


class KernelModuleParameter(Model):
    topic = SystemInfoTopic

    name = fields.String()
    value = fields.String()


class ActiveKernelModule(Model):
    topic = SystemInfoTopic

    filename = fields.String()
    parameters = fields.List(fields.Model(KernelModuleParameter))
    signature = fields.Nullable(fields.String())


class SELinux(Model):
    topic = SystemInfoTopic

    runtime_mode = fields.StringEnum(['enforcing', 'permissive'])
    static_mode = fields.StringEnum(['enforcing', 'permissive', 'disabled'])
    enabled = fields.Boolean()
    policy = fields.String()
    mls_enabled = fields.Boolean()


class FirewallStatus(Model):
    topic = SystemInfoTopic

    enabled = fields.Boolean()
    active = fields.Boolean()


class Firewalls(Model):
    topic = SystemInfoTopic

    firewalld = fields.Model(FirewallStatus)
    iptables = fields.Model(FirewallStatus)


class SystemFacts(Model):
    topic = SystemInfoTopic

    sysctl_variables = fields.List(fields.Model(SysctlVariable))
    kernel_modules = fields.List(fields.Model(ActiveKernelModule))
    users = fields.List(fields.Model(User))
    groups = fields.List(fields.Model(Group))
    repositories = fields.List(fields.Model(Repositories))
    selinux = fields.Model(SELinux)
    firewalls = fields.Model(Firewalls)
