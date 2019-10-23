# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import os.path as ph

from leapp.libraries.actor.utils import (
    NotNSSConfiguration,
    InsufficientTooling
)
from leapp.libraries.actor.openldap import Openldap


class SssdServices(object):
    OPTS = [('pam', 'pam_cert_db_path'),
            ('ssh', 'ca_db')]

    def __init__(self, log, sssd_module, sssd, ol):
        self.sssd_module = sssd_module
        self._sssd = sssd
        self._ol = ol

    def _read(self):
        values = {}
        for service, option in self.OPTS:
            try:
                values[(service, option)] = self._sssd.get_service(service).get_option(option)
            except (self.sssd_module.NoServiceError, self.sssd_module.NoOptionError):
                values[(service, option)] = None
        return values

    def _fix(self, conf):
        for key, value in conf.items():
            service, option = key
            try:
                self._sssd.new_service(service)
            except self.sssd_module.ServiceAlreadyExistsError:
                pass  # ok, since we're just updating an existing service
            s = self._sssd.get_service(service)
            s.set_option(option, value)
            self._sssd.save_service(s)
        self._sssd.write()

    def process(self):
        try:
            old_confs = self._read()
            new_confs = {}
            for key, value in old_confs.items():
                try:
                    conf = Openldap.TLSConfiguration(cacertdir=value, cert=None, key=None)
                    new_confs[key] = self._ol.convert(conf)
                except NotNSSConfiguration:
                    pass  # we're lucky
            self._fix(new_confs)
        except (NotNSSConfiguration) as e:
            return (None, e)
        except BaseException as e:
            return (False, e)
        return (True,)


class SssdDomains(object):
    OPTS = {'ldap_tls_cacertdir': 'cacertdir',
            'ldap_tls_cert': 'cert',
            'ldap_tls_key': 'key'}

    def __init__(self, log, sssd_module, sssd, ol):
        self.sssd_module = sssd_module
        self._sssd = sssd
        self._ol = ol

    def _read(self):
        domains = [self._sssd.get_domain(d) for d in self._sssd.list_domains()]
        confs = {}
        for d in domains:
            confs[d.name] = {}
            for so, lo in self.OPTS.items():
                try:
                    confs[d.name][lo] = d.get_option(so)
                except self.sssd_module.NoOptionError:
                    confs[d.name][lo] = None
        return {domain: Openldap.TLSConfiguration(**attrs) for domain, attrs in confs.items()}

    def _fix(self, confs):
        domains = [self._sssd.get_domain(d) for d in self._sssd.list_domains()]
        for d in domains:
            for so, lo in self.OPTS.items():
                val = confs[d.name]._asdict()[lo]
                if val is not None:
                    d.set_option(so, val)
            self._sssd.save_domain(d)
        self._sssd.write()

    def process(self):
        try:
            old_confs = self._read()
            new_confs = {}
            for name, conf in old_confs.items():
                try:
                    new_confs[name] = self._ol.convert(conf)
                except NotNSSConfiguration:
                    pass  # no need to convert
            self._fix(new_confs)
        except (NotNSSConfiguration) as e:
            return (None, e)
        except BaseException as e:
            return (False, e)
        return (True,)


class Sssd(object):

    def __init__(self, log, config_file='/etc/sssd/sssd.conf'):
        self._log = log

        try:
            self.sssd_module = __import__('SSSDConfig')
        except ImportError:
            raise InsufficientTooling('Could not import python module SSSDConfig')

        self._ol = Openldap(log)
        self._sssd = self.sssd_module.SSSDConfig()
        self.config_file = config_file
        if not ph.exists(self.config_file):
            raise NotNSSConfiguration('SSSD configuration file missing - skipping conversion.')
        self._sssd.import_config(self.config_file)

        params = [self._log, self.sssd_module, self._sssd, self._ol]
        self.domains = SssdDomains(*params)
        self.services = SssdServices(*params)

    def process(self):
        self.domains.process()
        self.services.process()


def process(logger):
    try:
        s = Sssd(logger)
    except BaseException as e:
        return (False, e)
    return s.process()
