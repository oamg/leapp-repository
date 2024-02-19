import glob
import os
import shutil

from leapp.actors import Actor
from leapp.models import SatelliteFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag

POSTGRESQL_DATA_PATH = '/var/lib/pgsql/data/'
POSTGRESQL_SCL_DATA_PATH = '/var/opt/rh/rh-postgresql12/lib/pgsql/data/'
POSTGRESQL_USER = 'postgres'
POSTGRESQL_GROUP = 'postgres'


class SatelliteUpgradeDataMigration(Actor):
    """
    Migrate Satellite PostgreSQL data
    """

    name = 'satellite_upgrade_data_migration'
    consumes = (SatelliteFacts,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag)

    def process(self):
        facts = next(self.consume(SatelliteFacts), None)
        if not facts or not facts.has_foreman:
            return

        if facts.postgresql.local_postgresql and os.path.exists(POSTGRESQL_SCL_DATA_PATH):
            # we can assume POSTGRESQL_DATA_PATH exists and is empty
            # move PostgreSQL data to the new home
            for item in glob.glob(os.path.join(POSTGRESQL_SCL_DATA_PATH, '*')):
                try:
                    shutil.move(item, POSTGRESQL_DATA_PATH)
                except Exception as e:  # pylint: disable=broad-except
                    self.log.warning('Failed moving PostgreSQL data: {}'.format(e))
                    return

            if not facts.postgresql.same_partition:
                for dirpath, _, filenames in os.walk(POSTGRESQL_DATA_PATH):
                    try:
                        shutil.chown(dirpath, POSTGRESQL_USER, POSTGRESQL_GROUP)
                        for filename in filenames:
                            shutil.chown(os.path.join(dirpath, filename), POSTGRESQL_USER, POSTGRESQL_GROUP)
                    except Exception as e:  # pylint: disable=broad-except
                        self.log.warning('Failed fixing ownership of PostgreSQL data: {}'.format(e))
                        return
