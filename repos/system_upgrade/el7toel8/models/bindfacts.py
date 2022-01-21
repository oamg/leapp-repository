from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class BindConfigIssuesModel(Model):
    """
    Problematic files with statements, which are problematic
    """

    topic = SystemInfoTopic
    path = fields.String()  # path to problematic file
    statements = fields.List(fields.String())  # list of offending statements


class BindFacts(Model):
    """
    Whole facts related to BIND configuration
    """

    topic = SystemInfoTopic

    # Detected configuration files via includes
    config_files = fields.List(fields.String())

    # Files modified by update
    modified_files = fields.List(fields.String())

    # Only issues detected.
    # unsupported dnssec-lookaside statements with old values
    # found in list of files. List of files, where unsupported
    # statements were found. Context not yet provided
    dnssec_lookaside = fields.Nullable(fields.List(fields.Model(BindConfigIssuesModel)))

    # Missing listen-on-v6 option
    listen_on_v6_missing = fields.Boolean(default=False)
