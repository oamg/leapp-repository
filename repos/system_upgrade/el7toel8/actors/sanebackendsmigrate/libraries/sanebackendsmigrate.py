from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM

# Database of changes in configuration files of sane-backends
# between RHELs

CANON_DR = [
    '# P-150M',
    'usb 0x1083 0x162c',
    '# DR-M160',
    'option extra-status 1',
    'option duplex-offset 400',
    'usb 0x1083 0x163e',
    '# DR-M140',
    'option extra-status 1',
    'option duplex-offset 400',
    'usb 0x1083 0x163f',
    '# DR-C125',
    'option duplex-offset 400',
    'usb 0x1083 0x1640',
    '# DR-P215',
    'usb 0x1083 0x1641',
    '# FSU-201',
    'usb 0x1083 0x1648',
    '# DR-C130',
    'usb 0x1083 0x164a',
    '# DR-P208',
    'usb 0x1083 0x164b',
    '# DR-G1130',
    'option buffer-size 8000000',
    'usb 0x1083 0x164f',
    '# DR-G1100',
    'option buffer-size 8000000',
    'usb 0x1083 0x1650',
    '# DR-C120',
    'usb 0x1083 0x1651',
    '# P-201',
    'usb 0x1083 0x1652',
    '# DR-F120',
    'option duplex-offset 1640',
    'usb 0x1083 0x1654',
    '# DR-M1060',
    'usb 0x1083 0x1657',
    '# DR-C225',
    'usb 0x1083 0x1658',
    '# DR-P215II',
    'usb 0x1083 0x1659',
    '# P-215II',
    'usb 0x1083 0x165b',
    '# DR-P208II',
    'usb 0x1083 0x165d',
    '# P-208II',
    'usb 0x1083 0x165f'
]

CARDSCAN = [
    '# Sanford Cardscan 800c',
    'usb 0x0451 0x6250'
]

DLL = ['epsonds']

EPJITSU = [
    '# Fujitsu fi-65F',
    'firmware /usr/share/sane/epjitsu/65f_0A01.nal',
    'usb 0x04c5 0x11bd',
    '# Fujitsu S1100',
    'firmware /usr/share/sane/epjitsu/1100_0B00.nal',
    'usb 0x04c5 0x1200',
    '# Fujitsu S1300i',
    'firmware /usr/share/sane/epjitsu/1300i_0D12.nal',
    'usb 0x04c5 0x128d',
    '# Fujitsu S1100i',
    'firmware /usr/share/sane/epjitsu/1100i_0A00.nal',
    'usb 0x04c5 0x1447'
]

FUJITSU = [
    '#fi-6125',
    'usb 0x04c5 0x11ee',
    '#fi-6225',
    'usb 0x04c5 0x11ef',
    '#ScanSnap SV600',
    'usb 0x04c5 0x128e',
    '#fi-7180',
    'usb 0x04c5 0x132c',
    '#fi-7280',
    'usb 0x04c5 0x132d',
    '#fi-7160',
    'usb 0x04c5 0x132e',
    '#fi-7260',
    'usb 0x04c5 0x132f',
    '#ScanSnap iX500EE',
    'usb 0x04c5 0x13f3',
    '#ScanSnap iX100',
    'usb 0x04c5 0x13f4',
    '#ScanPartner SP25',
    'usb 0x04c5 0x1409',
    '#ScanPartner SP30',
    'usb 0x04c5 0x140a',
    '#ScanPartner SP30F',
    'usb 0x04c5 0x140c',
    '#fi-6140ZLA',
    'usb 0x04c5 0x145f',
    '#fi-6240ZLA',
    'usb 0x04c5 0x1460',
    '#fi-6130ZLA',
    'usb 0x04c5 0x1461',
    '#fi-6230ZLA',
    'usb 0x04c5 0x1462',
    '#fi-6125ZLA',
    'usb 0x04c5 0x1463',
    '#fi-6225ZLA',
    'usb 0x04c5 0x1464',
    '#fi-6135ZLA',
    'usb 0x04c5 0x146b',
    '#fi-6235ZLA',
    'usb 0x04c5 0x146c',
    '#fi-6120ZLA',
    'usb 0x04c5 0x146d',
    '#fi-6220ZLA',
    'usb 0x04c5 0x146e',
    '#N7100',
    'usb 0x04c5 0x146f',
    '#fi-6400',
    'usb 0x04c5 0x14ac',
    '#fi-7480',
    'usb 0x04c5 0x14b8',
    '#fi-6420',
    'usb 0x04c5 0x14bd',
    '#fi-7460',
    'usb 0x04c5 0x14be',
    '#fi-7140',
    'usb 0x04c5 0x14df',
    '#fi-7240',
    'usb 0x04c5 0x14e0',
    '#fi-7135',
    'usb 0x04c5 0x14e1',
    '#fi-7235',
    'usb 0x04c5 0x14e2',
    '#fi-7130',
    'usb 0x04c5 0x14e3',
    '#fi-7230',
    'usb 0x04c5 0x14e4',
    '#fi-7125',
    'usb 0x04c5 0x14e5',
    '#fi-7225',
    'usb 0x04c5 0x14e6',
    '#fi-7120',
    'usb 0x04c5 0x14e7',
    '#fi-7220',
    'usb 0x04c5 0x14e8',
    '#fi-400F',
    'usb 0x04c5 0x151e',
    '#fi-7030',
    'usb 0x04c5 0x151f',
    '#fi-7700',
    'usb 0x04c5 0x1520',
    '#fi-7600',
    'usb 0x04c5 0x1521',
    '#fi-7700S',
    'usb 0x04c5 0x1522'
]

CANON = [
    '# Canon LiDE 80',
    'usb 0x04a9 0x2214',
    '# Canon LiDE 120',
    'usb 0x04a9 0x190e',
    '# Canon LiDE 220',
    'usb 0x04a9 0x190f'
]

XEROX_MFP = [
    '#Samsung X4300 Series',
    'usb 0x04e8 0x3324',
    '#Samsung K4350 Series',
    'usb 0x04e8 0x3325',
    '#Samsung X7600 Series',
    'usb 0x04e8 0x3326',
    '#Samsung K7600 Series',
    'usb 0x04e8 0x3327',
    '#Samsung K703 Series',
    'usb 0x04e8 0x3331',
    '#Samsung X703 Series',
    'usb 0x04e8 0x3332',
    '#Samsung M458x Series',
    'usb 0x04e8 0x346f',
    '#Samsung M4370 5370 Series',
    'usb 0x04e8 0x3471',
    '#Samsung X401 Series',
    'usb 0x04e8 0x3477',
    '#Samsung K401 Series',
    'usb 0x04e8 0x3478',
    '#Samsung K3250 Series',
    'usb 0x04e8 0x3481',
    '#Samsung X3220 Series',
    'usb 0x04e8 0x3482'
]

NEW_QUIRKS = {
    '/etc/sane.d/canon_dr.conf': CANON_DR,
    '/etc/sane.d/cardscan.conf': CARDSCAN,
    '/etc/sane.d/dll.conf': DLL,
    '/etc/sane.d/epjitsu.conf': EPJITSU,
    '/etc/sane.d/fujitsu.conf': FUJITSU,
    '/etc/sane.d/canon.conf': CANON,
    '/etc/sane.d/xerox_mfp.conf': XEROX_MFP
}
"""
Dictionary of configuration files which changes in 1.0.27
"""


def _macro_exists(path, macro):
    """
    Check if macro is in the file.

    :param str path: string representing the full path of the config file
    :param str macro: new directive to be added
    :return boolean res: macro does/does not exist in the file
    """
    with open(path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        if line.lstrip().startswith(macro):
            return True
    return False


def _append_string(path, content):
    """
    Append string at the end of file.

    :param str path: string representing the full path of file
    :param str content: preformatted string to be added
    """
    with open(path, 'a') as f:
        f.write(content)


def update_config(path,
                  quirks,
                  check_function=_macro_exists,
                  append_function=_append_string):
    """
    Insert expected content into the file on the path if it is not
    in the file already.

    :param str path: string representing the full path of the config file
    :param func check_function: function to be used to check if string is in the file
    :param func append_function: function to be used to append string
    """

    macros = []
    for macro in quirks:
        if not check_function(path, macro):
            macros.append(macro)

    if not macros:
        return

    fmt_input = "\n{comment_line}\n{content}\n".format(comment_line='# content added by Leapp',
                                                       content='\n'.join(macros))

    try:
        append_function(path, fmt_input)
    except IOError:
        raise IOError('Error during writing to file: {}.'.format(path))


def _check_package(pkg_name):
    """
    Checks if the package is installed and signed by Red Hat

    :param str pkg_name: name of package
    """

    return has_package(InstalledRedHatSignedRPM, pkg_name)


def update_sane(debug_log=api.current_logger().debug,
                error_log=api.current_logger().error,
                is_installed=_check_package,
                append_function=_append_string,
                check_function=_macro_exists):
    """
    Iterate over dictionary and updates each configuration file.

    :param func debug_log: function for debug logging
    :param func error_log: function for error logging
    :param func is_installed: checks if the package is installed
    :param func append_function: appends a string into file
    :param func check_function: checks if a string exists in file
    """

    error_list = []

    if not is_installed('sane-backends'):
        return

    for path, lines in NEW_QUIRKS.items():

        debug_log('Updating SANE configuration file {}.'.format(path))

        try:
            update_config(path, lines, check_function, append_function)
        except (OSError, IOError) as error:
            error_list.append((path, error))

    if error_list:
        error_log('The files below have not been modified '
                  '(error message included):' +
                  ''.join(['\n    - {}: {}'.format(err[0], err[1])
                          for err in error_list]))
        return
