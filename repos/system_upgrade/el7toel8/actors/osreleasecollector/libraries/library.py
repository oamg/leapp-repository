from leapp.libraries.common import requirearchver
from leapp.models import OSReleaseFacts


def get_os_release_model(path):
    """Return model created from OS release info from provided file."""
    data = requirearchver.get_os_release_info(path)

    return OSReleaseFacts(
        release_id=data.get('ID', ''),
        name=data.get('NAME', ''),
        pretty_name=data.get('PRETTY_NAME', ''),
        version=data.get('VERSION', ''),
        version_id=data.get('VERSION_ID', ''),
        variant=data.get('VARIANT', '') or None,
        variant_id=data.get('VARIANT_ID', '') or None
    )
