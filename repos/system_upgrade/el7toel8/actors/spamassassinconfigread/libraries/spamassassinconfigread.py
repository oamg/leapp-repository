from leapp.libraries.actor import spamassassinconfigread_spamc, spamassassinconfigread_spamd
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, SpamassassinFacts


def is_processable():
    """
    Checks whether the spamassassin package is installed.
    """
    res = has_package(InstalledRedHatSignedRPM, 'spamassassin')
    if not res:
        api.current_logger().debug('spamassassin is not installed.')
    return res


def get_spamassassin_facts(read_func, listdir):
    """
    Reads the spamc configuration file, the spamassassin sysconfig file and checks
    whether the spamassassin service is overridden. Returns SpamassassinFacts.
    """
    spamc_ssl_argument = spamassassinconfigread_spamc.get_spamc_ssl_argument(read_func)
    service_overriden = spamassassinconfigread_spamd.spamassassin_service_overriden(listdir)
    spamd_ssl_version = spamassassinconfigread_spamd.get_spamd_ssl_version(read_func)
    return SpamassassinFacts(spamc_ssl_argument=spamc_ssl_argument,
                             service_overriden=service_overriden,
                             spamd_ssl_version=spamd_ssl_version)
