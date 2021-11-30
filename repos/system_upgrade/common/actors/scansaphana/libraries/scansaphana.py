from os import listdir, path

from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SapHanaInfo, SapHanaInstanceInfo, SapHanaManifestEntry

HANA_BASE_PATH = '/hana/shared'
HANA_MANIFEST_PATH = 'exe/linuxx86_64/hdb/manifest'
HANA_SAPCONTROL_PATH = 'exe/linuxx86_64/hdb/sapcontrol'


def perform_sap_hana_scan():
    """
    Produces a message with details collected around SAP HANA.
    """

    api.produce(search_sap_hana_instances())


def parse_manifest(path):
    """ Parses a SAP HANA manifest into a dictionary """
    def _decoded(s):
        """
        Compatibility between Python2 and 3 - Python 2 has no str.decode but we can process str directly.
        Python3 needs the byte data to be decoded so we can process the string data.
        """
        if hasattr(s, 'decode'):
            return s.decode('utf-8')
        return s

    data = []
    try:
        with open(path, 'r') as f:
            for line in _decoded(f.read()).split('\n'):
                try:
                    key, value = line.split(':', 1)
                except ValueError:
                    # Most likely an empty line, but we're being permissive here and ignore failures.
                    # In the end it's all about having the right values available.
                    if line:
                        api.current_logger().warn(
                            'Failed to parse line in manifest: {file}. Line was: `{line}`'.format(file=path,
                                                                                                  line=line),
                            exc_info=True)
                    continue
                data.append(SapHanaManifestEntry(key=key, value=value.strip()))
    except OSError:
        return None
    return data


def search_sap_hana_instances():
    """
    Searches for all instances of SAP HANA on the system and gets the information for it

    This code will go through all entries in /hana/shared and checks for all instances within.
    For each instance it will check the status and record the location.

    :return: SapHanaInfo
    """
    # Keeps track of found instances
    result = []
    # Keeps track if any instance is running
    any_running = False
    # Keeps track if any SAP HANA installation was found. In theory it could be also derived from len(result) != 0
    installed = False
    if path.isdir(HANA_BASE_PATH):
        for entry in listdir(HANA_BASE_PATH):

            entry_path = path.join(HANA_BASE_PATH, entry)
            sapcontrol_path = path.join(entry_path, HANA_SAPCONTROL_PATH)
            entry_manifest_path = path.join(entry_path, HANA_MANIFEST_PATH)
            if path.isfile(entry_manifest_path):
                # We found the manifest file in the expected relative path.
                # Now we are going to look for instance directories.
                for instance in listdir(entry_path):
                    instance_number = None
                    if 'HDB' in instance:
                        # We found an instance. Instance directories follow HDB[0-9][0-9] naming pattern,
                        # where the numbers represent the instance number.
                        instance_number = instance[-2:]
                    if not instance_number:
                        # This is not a folder we are interested in
                        continue
                    # Now obviously SAP HANA is installed
                    installed = True
                    # We can derive the admin name from `entry` directory name
                    admin_name = '{}adm'.format(entry.lower())
                    # Retrieving the status of this instance
                    running = get_instance_status(instance_number, sapcontrol_path, admin_name)
                    # Update the variable that tracks all instances if any is running.
                    # This makes the inhibitor code easier later.
                    any_running = any_running or running
                    # Append the found instance to the list
                    result.append(
                        SapHanaInstanceInfo(
                            name=entry,
                            manifest=parse_manifest(entry_manifest_path),
                            path=entry_path,
                            instance_number=instance_number,
                            running=running,
                            admin=admin_name
                        )
                    )
    # Return the results
    return SapHanaInfo(instances=result, running=any_running, installed=installed)


def get_instance_status(instance_number, sapcontrol_path, admin_name):
    """ Gets the status for the instance given """
    try:
        # Executes sapcontrol in the context of the instance admin user to retrieve the process list for the given
        # SAP HANA instance.
        # GetProcessList has some oddities, like returning non zero exit codes with special meanings.
        # Exit code 3 = All processes are running correctly
        # Exit code 4 = All processes stopped
        # Other exit codes aren't handled at this time and it's assumed that SAP HANA is possibly in some unusal
        # state. Such as starting/stopping but also that it is in some kind of failure state.
        output = run([
            'sudo', '-u', admin_name, sapcontrol_path, '-nr', instance_number, '-function', 'GetProcessList'],
            checked=False)
        if output['exit_code'] == 3:
            # GetProcessList succeeded, all processes running correctly
            return True
        if output['exit_code'] == 4:
            # GetProcessList succeeded, all processes stopped
            return False
        # SAP HANA might be somewhere in between (Starting/Stopping)
        # In that case there are always more than 7 lines.
        return len(output['stdout'].split('\n')) > 7
    except CalledProcessError:
        api.current_logger().warn(
            'Failed to retrieve SAP HANA instance status from sapcontrol - Considering it as not running.')
        return False
