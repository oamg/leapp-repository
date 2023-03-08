import os

import six

from leapp.actors import Actor
from leapp.models import InvalidRootSubdirectory, RootDirectory, RootSubdirectory
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class RootScanner(Actor):
    """
    Scan the system root directory and produce a message containing
    information about its subdirectories.
    """

    name = 'root_scanner'
    consumes = ()
    produces = (RootDirectory,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        subdirs = []
        invalid_subdirs = []

        def _create_a_subdir(subdir_cls, name, path):
            if os.path.islink(path):
                return subdir_cls(name=name, target=os.readlink(path))
            return subdir_cls(name=name)

        for subdir in os.listdir('/'):
            # Note(ivasilev) in py3 env non-utf encoded string will appear as byte strings
            # However in py2 env subdir will be always of str type, so verification if this is a valid utf-8 string
            # should be done differently than formerly suggested plain six.binary_type check
            decoded = True
            if isinstance(subdir, six.binary_type):
                try:
                    subdir.decode('utf-8')
                except (AttributeError, UnicodeDecodeError):
                    decoded = False
            if not decoded:
                invalid_subdirs.append(_create_a_subdir(InvalidRootSubdirectory, subdir, os.path.join(b'/', subdir)))
            else:
                subdirs.append(_create_a_subdir(RootSubdirectory, subdir, os.path.join('/', subdir)))

        self.produce(RootDirectory(items=subdirs, invalid_items=invalid_subdirs))
