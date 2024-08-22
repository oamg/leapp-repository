from leapp.actors import Actor
from leapp.libraries.actor import convertgrubenvtofile
from leapp.models import ConvertGrubenvTask
from leapp.tags import FinalizationPhaseTag, IPUWorkflowTag


class ConvertGrubenvToFile(Actor):
    """
    Convert "grubenv" symlink to a regular file on Azure hybrid images using BIOS.

    For more information see CheckGrubenvToFile actor.

    """

    name = 'convert_grubenv_to_file'
    consumes = (ConvertGrubenvTask,)
    produces = ()
    tags = (FinalizationPhaseTag, IPUWorkflowTag)

    def process(self):
        convertgrubenvtofile.process()
