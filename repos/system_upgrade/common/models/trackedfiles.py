from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class FileInfo(Model):
    """
    Various data about a file.

    This model is not supposed to be used as a message directly.
    See e.g. :class:`TrackedSourceFilesInfo` instead.
    """
    topic = SystemInfoTopic

    path = fields.String()
    """
    Canonical path to the file.
    """

    exists = fields.Boolean()
    """
    True if the file is present on the system.
    """

    rpm_name = fields.String(default="")
    """
    Name of the rpm that owns the file. Otherwise empty string if not owned
    by any rpm.
    """

    # NOTE(pstodulk): I have been thinking about the "state"/"modified" field
    # instead. Which could contain enum list, where could be specified what has
    # been changed (checksum, type, owner, ...). But currently we do not have
    # use cases for that and do not want to implement it now. So starting simply
    # with this one.
    is_modified = fields.Boolean()
    """
    True if the checksum of the file has been changed (includes the missing state).

    The field is valid only for a file tracked by rpm - excluding ghost files.
    In such a case the value is always false.
    """


class TrackedFilesInfoSource(Model):
    """
    Provide information about files on the source system explicitly defined
    in the actor to be tracked.

    Search an actor producing this message to discover the list where you
    could add the file into the list to be tracked.

    This particular message is expected to be produced only once by the
    specific actor. Do not produce multiple messages of this model.
    """
    topic = SystemInfoTopic

    files = fields.List(fields.Model(FileInfo), default=[])
    """
    List of :class:`FileInfo`.
    """
