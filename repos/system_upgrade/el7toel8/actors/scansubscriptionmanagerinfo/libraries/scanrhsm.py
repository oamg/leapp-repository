from leapp.models import SourceRHSMInfo
from leapp.libraries.common import rhsm
from leapp.libraries.common.mounting import NotIsolatedActions
from leapp.libraries.stdlib import api


@rhsm.with_rhsm
def scan():
    info = SourceRHSMInfo()
    context = NotIsolatedActions(base_dir='/')
    rhsm.scan_rhsm_info(context, info)
    api.produce(info)
