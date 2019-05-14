import io

from leapp.actors import Actor
from leapp.exceptions import CalledProcessError
from leapp.libraries.stdlib import run
from leapp.models import NetworkManagerConfig
from leapp.tags import IPUWorkflowTag, FactsPhaseTag
from six.moves.configparser import ConfigParser, ParsingError


class NetworkManagerReadConfig(Actor):
    """
    Provides data about NetworkManager configuration.

    After collecting data from NetworkManager tool, a message with relevant data will be produced.
    """

    name = 'network_manager_read_config'
    consumes = ()
    produces = (NetworkManagerConfig,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        nm_config = NetworkManagerConfig()
        try:
            # Use 'NM --print-config' to read the configurationo so
            # that the main configuration file and other files in
            # various directories get merged in the right way.
            r = run(['NetworkManager', '--print-config'], split=False)['stdout']
        except CalledProcessError as e:
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
