import os

from leapp.libraries.stdlib import api
from leapp.models import NISConfig

PACKAGES_NAMES = ('ypserv', 'ypbind')
YPBIND_CONF_FILE = '/etc/yp.conf'
YPSERV_DIR_PATH = '/var/yp'
YPSERV_DEFAULT_FILES = ('binding', 'Makefile', 'nicknames')


class NISScanLibrary:
    """
    Helper library for NISScan actor.
    """

    def client_has_non_default_configuration(self):
        """
        Check for any significant ypbind configuration lines in .conf file.
        """
        if not os.path.isfile(YPBIND_CONF_FILE):
            return False

        # Filter whitespaces and empty lines
        with open(YPBIND_CONF_FILE) as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        for line in lines:
            # Checks for any valid configuration entry
            if not line.startswith('#'):
                return True
        return False

    def server_has_non_default_configuration(self):
        """
        Check for any additional (not default) files in ypserv DIR.
        """
        if not os.path.isdir(YPSERV_DIR_PATH):
            return False

        return any(f not in YPSERV_DEFAULT_FILES for f in os.listdir(YPSERV_DIR_PATH))

    def process(self):
        """
        Check NIS pkgs configuration for the following options:

        - yp.conf custom configuration
        - /var/yp not default entry
        """
        pkgs = []

        if self.server_has_non_default_configuration():
            pkgs.append('ypserv')

        if self.client_has_non_default_configuration():
            pkgs.append('ypbind')

        api.produce(NISConfig(nis_not_default_conf=pkgs))
