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

        if facts.postgresql.local_postgresql:
            api.current_actor().show_message('Re-indexing the database. This can take a while.')
            try:
                run(['sed', '-i', '/data_directory/d', '/var/lib/pgsql/data/postgresql.conf'])
                run(['systemctl', 'start', 'postgresql'])
                run(['runuser', '-u', 'postgres', '--', 'reindexdb', '-a'])
            except CalledProcessError as e:
                api.current_logger().error('Failed to reindex the database: {}'.format(str(e)))

        installer_cmd = ['foreman-installer']
        if facts.has_katello_installer:
            installer_cmd.append('--disable-system-checks')

        api.current_actor().show_message('Running the installer. This can take a while.')
        try:
            run(installer_cmd)
        except OSError as e:
            api.current_logger().error('Failed to run `foreman-installer`: {}'.format(str(e)))
        except CalledProcessError:
            api.current_logger().error(
                'Could not run the installer, please inspect the logs in /var/log/foreman-installer!'
            )
