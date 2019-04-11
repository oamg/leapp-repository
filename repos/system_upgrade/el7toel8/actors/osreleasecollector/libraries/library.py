from leapp.libraries.common import reporting
from leapp.models import OSReleaseFacts


def get_os_release_info(path):
    ''' Retrieve data about System OS release from provided file '''
    data = {}
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
    except IOError as e:
        reporting.report_generic(
            title='Error while collecting system OS facts',
            summary=str(e),
            severity='high',
            flags=['inhibitor'])
        return None

    return OSReleaseFacts(
        id=data.get('ID', '').strip('"'),
        name=data.get('NAME', '').strip('"'),
        pretty_name=data.get('PRETTY_NAME', '').strip('"'),
        version=data.get('VERSION', '').strip('"'),
        version_id=data.get('VERSION_ID', '').strip('"'),
        variant=data.get('VARIANT', '').strip('"') or None,
        variant_id=data.get('VARIANT_ID', '').strip('"') or None
    )
