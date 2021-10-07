from leapp.actors import Actor
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SatelliteFacts
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class SatelliteUpgrader(Actor):
    """
    Execute installer in the freshly booted system, to finalize Satellite configuration
    """

    name = 'satellite_upgrader'
    consumes = (SatelliteFacts, )
    produces = ()
    tags = (IPUWorkflowTag, FirstBootPhaseTag)

    def process(self):
        facts = next(self.consume(SatelliteFacts), None)
        if not facts or not facts.has_foreman:
            return

        api.current_actor().show_message('Running the installer. This can take a while.')
        try:
            run(['foreman-installer'])
        except OSError as e:
            api.current_logger().error('Failed to run `foreman-installer`: {}'.format(str(e)))
        except CalledProcessError:
            api.current_logger().error(
                'Could not run the installer, please inspect the logs in /var/log/foreman-installer!'
            )
