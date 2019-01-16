import io
from subprocess import CalledProcessError

from leapp.actors import Actor
from leapp.libraries.stdlib import call
from leapp.models import NetworkManagerConfig
from leapp.tags import IPUWorkflowTag, FactsPhaseTag
from six.moves.configparser import ConfigParser, ParsingError


class NetworkManagerReadConfig(Actor):
    name = 'network_manager_read_config'
    description = 'This actor reads NetworkManager configuration.'
    consumes = ()
    produces = (NetworkManagerConfig,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        nm_config = NetworkManagerConfig()
        try:
            # Use 'NM --print-config' to read the configurationo so
            # that the main configuration file and other files in
            # various directories get merged in the right way.
            r = call(['NetworkManager', '--print-config'], split=False)
        except (OSError, CalledProcessError) as e:
            self.log.warning('Error reading NetworkManager configuration: {}'.format(e))
            return

        parser = ConfigParser()

        try:
            if hasattr(parser, 'read_string'):
                 # Python 3
                parser.read_string(r)
            else:
                 # Python 2
                from cStringIO import StringIO
                parser.readfp(StringIO(r))
        except ParsingError as e:
            self.log.warning('Error parsing NetworkManager configuration: {}'.format(e))
            return

        if parser.has_option('main', 'dhcp'):
            nm_config.dhcp = parser.get("main", "dhcp")

        self.produce(nm_config)
