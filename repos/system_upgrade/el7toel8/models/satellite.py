from leapp.models import fields, Model
from leapp.topics import SystemFactsTopic


class SatellitePostgresqlFacts(Model):
    topic = SystemFactsTopic

    local_postgresql = fields.Boolean(default=True)
    """ Whether or not PostgreSQL is installed on the same system """
    old_var_lib_pgsql_data = fields.Boolean(default=False)
    """ Whether or not there is old PostgreSQL data in /var/lib/pgsql/data """
    same_partition = fields.Boolean(default=True)
    """ Whether or not target and source postgresql data will stay on the same partition """
    space_required = fields.Nullable(fields.Integer())
    """ How many bytes are required on the target partition """
    space_available = fields.Nullable(fields.Integer())
    """ How many bytes are available on the target partition """


class SatelliteFacts(Model):
    topic = SystemFactsTopic

    has_foreman = fields.Boolean(default=False)
    """Whether or not foreman is installed on this system"""
    has_katello_installer = fields.Boolean(default=True)
    """Whether or not the installer supports Katello additions"""
    postgresql = fields.Model(SatellitePostgresqlFacts)
    """ Foreman related PostgreSQL facts """
