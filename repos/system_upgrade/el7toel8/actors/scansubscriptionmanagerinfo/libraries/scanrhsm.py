from leapp.libraries.common import rhsm
from leapp.libraries.common.mounting import NotIsolatedActions
from leapp.libraries.stdlib import api


@rhsm.with_rhsm
def scan():
    context = NotIsolatedActions(base_dir='/')
    info = rhsm.scan_rhsm_info(context)
    api.produce(info)
