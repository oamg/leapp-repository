import json

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api
from leapp.models import IPUPath, IPUPaths
from leapp.utils.deprecation import suppress_deprecation


def load_ipu_paths_for_flavour(flavour, _filename='upgrade_paths.json'):
    """
    Load defined IPU paths from the upgrade_paths.json file for the specified
    flavour.

    Note the file is required to be always present, so skipping any test
    for the missing file. Crash hard and terribly if the file is missing
    or the content is invalid.

    We expect the flavour to be always good as it is under our control
    (already sanitized in IPUConfig), but return empty dict and log it if missing.
    """
    with open(api.get_common_file_path(_filename)) as fp:
        data = json.loads(fp.read())
    if flavour not in data:
        api.current_logger().warning(
            'Cannot discover any upgrade paths for flavour: {}'
            .format(flavour)
        )
    return data.get(flavour, {})


def get_filtered_ipu_paths(ipu_paths, src_major_version):
    result = []
    for src_version, tgt_versions in ipu_paths.items():
        if src_version.split('.')[0] == src_major_version:
            result.append(IPUPath(source_version=src_version, target_versions=tgt_versions))
    return result


@suppress_deprecation(IPUPaths)
def process():
    flavour = api.current_actor().configuration.flavour
    ipu_paths = load_ipu_paths_for_flavour(flavour)
    api.produce(IPUPaths(data=get_filtered_ipu_paths(ipu_paths, get_source_major_version())))
