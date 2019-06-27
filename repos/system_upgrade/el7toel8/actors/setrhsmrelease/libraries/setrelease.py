from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import api
from leapp.models import TargetRHSMInfo


def process():
    info = next(api.consume(TargetRHSMInfo), None)
    if info:
        rhsm.set_release(mounting.NotIsolatedActions(base_dir='/'), info.release)
