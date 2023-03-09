from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import FIPSInfo


def read_sys_fips_state():
    with open('/proc/sys/crypto/fips_enabled') as fips_status_handle:
        return fips_status_handle.read().strip()


def check_fips_state_perserved():
    fips_info = next(api.consume(FIPSInfo), None)
    if not fips_info:
        # Unexpected, FIPSInfo is produced unconditionally
        raise StopActorExecutionError('Cannot check for the correct FIPS state in the upgrade initramfs',
                                      details={'Problem': 'Did not receive any FIPSInfo message'})

    if fips_info.is_enabled:
        fips_status = read_sys_fips_state()
        if fips_status != '1':
            details = {'details': ('The system is reporting FIPS as disabled, although it should be enabled'
                                   ' since it was enabled on the source system.')}
            raise StopActorExecutionError('Failed to enable FIPS in the upgrade initramfs', details=details)
