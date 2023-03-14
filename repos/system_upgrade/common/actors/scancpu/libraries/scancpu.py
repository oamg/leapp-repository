import re

from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import CPUInfo, DetectedDeviceOrDriver, DeviceDriverDeprecationData

LSCPU_NAME_VALUE = re.compile(r'(?P<name>[^:]+):\s+(?P<value>.+)\n?')
PPC64LE_MODEL = re.compile(r'\d+\.\d+ \(pvr (?P<family>[0-9a-fA-F]+) 0*[0-9a-fA-F]+\)')


def _get_lscpu_output():
    try:
        result = run(['lscpu'])
        return result.get('stdout', '')
    except (OSError, CalledProcessError):
        api.current_logger().debug('Executing `lscpu` failed', exc_info=True)
    return ''


def _get_cpu_flags(lscpu):
    flags = lscpu.get('Flags', '')
    return flags.split()


def _get_cpu_entries_for(arch_prefix):
    result = []
    for message in api.consume(DeviceDriverDeprecationData):
        result.extend([
            entry for entry in message.entries
            if entry.device_type == 'cpu' and entry.device_id.startswith(arch_prefix)
        ])
    return result


def _is_detected_aarch64(lscpu, entry):
    # Currently not applicable - We don't have a way to correctly detect this
    # But we should find a way to properly do so in future.

    # Shut up warnings:
    entry = lscpu
    lscpu = entry
    return False


def _is_detected_s390x(lscpu, entry):
    try:
        _, _, machine_type, _ = entry.device_id.split(':', 4)
        return machine_type == lscpu.get('Machine type')
    except ValueError:
        return False


def _is_detected_ppc64le(lscpu, entry):
    try:
        _, _, machine_type, _ = entry.device_id.split(':', 4)
        match = PPC64LE_MODEL.match(lscpu.get('Model'))
        if not match:
            return False
        family = match.group('family')
        return family and machine_type.lstrip('0').lower() == family.lstrip('0').lower()
    except ValueError:
        return False


def _make_set(value):
    """
    Converts range/set specification to a concrete set of numbers

    '[1-3]'         => {1, 2, 3}
    '{1,2,3}'       => {1, 2, 3}
    '{[1-3]}        => {1, 2, 3}
    '{[1-3],[5-7]}  => {1, 2, 3, 5, 6, 7}
    """
    result = set()
    for vrange in value.strip('{} ').split(','):
        if '[' not in vrange:
            try:
                result.add(int(vrange))
            except ValueError:
                pass
        else:
            try:
                start, end = vrange.strip('[] ').split('-')
                result.update(range(int(start.strip()), int(end.strip()) + 1))
            except ValueError:
                pass
    return result


def _match_model(needle, hay):
    try:
        ineedle = int(needle)
    except ValueError:
        return False
    if not hay or hay == '*':
        # Match all
        return True
    if '[' not in hay and '{' not in hay:
        return hay == needle
    return ineedle in _make_set(hay)


def _is_detected_x86_64(lscpu, entry):
    vendors = {'amd': 'AuthenticAMD', 'intel': 'GenuineIntel'}
    try:
        _, vendor, family, model = entry.device_id.split(':', 4)
        if vendor in vendors and vendors[vendor] == lscpu.get('Vendor ID'):
            if family == lscpu.get('CPU family'):
                return _match_model(lscpu.get('Model'), model)
        return False
    except ValueError:
        return False


def _to_detected_device(entry):
    return DetectedDeviceOrDriver(**entry.dump())


def _find_deprecation_data_entries(lscpu):
    arch_prefix, is_detected = None, None
    if architecture.matches_architecture(architecture.ARCH_X86_64):
        arch_prefix, is_detected = architecture.ARCH_X86_64, _is_detected_x86_64
    elif architecture.matches_architecture(architecture.ARCH_PPC64LE):
        arch_prefix, is_detected = architecture.ARCH_PPC64LE, _is_detected_ppc64le
    elif architecture.matches_architecture(architecture.ARCH_S390X):
        arch_prefix, is_detected = architecture.ARCH_S390X, _is_detected_s390x
    elif architecture.matches_architecture(architecture.ARCH_ARM64):
        arch_prefix, is_detected = architecture.ARCH_ARM64, _is_detected_aarch64

    if arch_prefix and is_detected:
        return [
            _to_detected_device(entry) for entry in _get_cpu_entries_for(arch_prefix)
            if is_detected(lscpu, entry)
        ]

    api.current_logger().warn('Unsupported platform could not detect relevant CPU information')
    return []


def process():
    lscpu = dict(LSCPU_NAME_VALUE.findall(_get_lscpu_output()))
    api.produce(*_find_deprecation_data_entries(lscpu))
    # Backwards compatibility
    machine_type = lscpu.get('Machine type')
    flags = _get_cpu_flags(lscpu)
    api.produce(
            CPUInfo(
                machine_type=int(machine_type) if machine_type else None,
                flags=flags
                )
            )
