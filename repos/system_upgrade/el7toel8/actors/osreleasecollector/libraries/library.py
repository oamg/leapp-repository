from leapp import reporting
from leapp.models import OSReleaseFacts


def get_os_release_info(path):
    ''' Retrieve data about System OS release from provided file '''
    data = {}
    try:
        with open(path) as f:
            data = dict(l.strip().split('=', 1) for l in f.readlines() if '=' in l)
    except IOError as e:
        reporting.create_report([
            reporting.Title('Error while collecting system OS facts'),
            reporting.Summary(str(e)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.SANITY]),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])
        return None

    return OSReleaseFacts(
        release_id=data.get('ID', '').strip('"'),
        name=data.get('NAME', '').strip('"'),
        pretty_name=data.get('PRETTY_NAME', '').strip('"'),
        version=data.get('VERSION', '').strip('"'),
        version_id=data.get('VERSION_ID', '').strip('"'),
        variant=data.get('VARIANT', '').strip('"') or None,
        variant_id=data.get('VARIANT_ID', '').strip('"') or None
    )
