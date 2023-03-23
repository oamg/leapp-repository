import os

import six

from leapp.models import InvalidRootSubdirectory, RootDirectory, RootSubdirectory


def scan_dir(root_dir=b'/'):
    """
    Scan root directory and return a RootDirectory(subdirs, invalid_subdirs) model object
    """
    subdirs = []
    invalid_subdirs = []

    def _create_a_subdir(subdir_cls, name, path):
        if os.path.islink(path):
            return subdir_cls(name=name, target=os.readlink(path))
        return subdir_cls(name=name)

    for subdir in os.listdir(root_dir):
        # Note(ivasilev) in py3 env non-utf encoded string will appear as byte strings
        # However in py2 env subdir will be always of str type, so verification if this is a valid utf-8 string
        # should be done differently than formerly suggested plain six.binary_type check
        decoded = True
        if isinstance(subdir, six.binary_type):
            try:
                subdir = subdir.decode('utf-8')
            except (AttributeError, UnicodeDecodeError):
                decoded = False
        if not decoded:
            invalid_subdirs.append(_create_a_subdir(InvalidRootSubdirectory, subdir, os.path.join(b'/', subdir)))
        else:
            subdirs.append(_create_a_subdir(RootSubdirectory, subdir, os.path.join('/', subdir)))
    return RootDirectory(items=subdirs, invalid_items=invalid_subdirs)
