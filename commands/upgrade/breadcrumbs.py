import datetime
import json
import os
import sys
from functools import wraps
from itertools import chain

from leapp import FULL_VERSION
from leapp.libraries.stdlib.call import _call
from leapp.utils.audit import get_messages

try:
    from json.decoder import JSONDecodeError  # pylint: disable=ungrouped-imports
except ImportError:
    JSONDecodeError = ValueError


def runs_in_container():
    """
    Check if the current process is running inside a container

    :return: True if the process is running inside a container, False otherwise
    """
    return os.path.exists('/run/host/container-manager')


def _flattened(d):
    """ Flatten nested dicts and lists into a single dict """
    def expand(key, value):
        if isinstance(value, dict):
            return [(key + '.' + k, v) for k, v in _flattened(value).items()]
        if isinstance(value, list):
            return chain(*[expand(key + '.' + str(i), v) for i, v in enumerate(value)])
        return [(key, value)]
    items = [item for k, v in d.items() for item in expand(k, v)]
    return dict(items)


class _BreadCrumbs(object):
    def __init__(self, activity):
        self._crumbs = {
            'activity': activity,
            'packages': self._get_packages(),
            'leapp_file_changes': [],
            'executed': ' '.join([v if ' ' not in v else '"{}"'.format(v) for v in sys.argv]),
            'success': True,
            'activity_started': datetime.datetime.utcnow().isoformat() + 'Z',
            'activity_ended': datetime.datetime.utcnow().isoformat() + 'Z',
            'source_os': '',
            'target_os': '',
            'env': dict(),
            'run_id': '',
            'version': FULL_VERSION,
        }

    def fail(self):
        self._crumbs['success'] = False

    def _save_rhsm_facts(self, activities):
        if not os.path.isdir('/etc/rhsm/facts'):
            if not os.path.exists('/etc/rhsm'):
                # If there's no /etc/rhsm folder just skip it
                return
            os.path.mkdir('/etc/rhsm/facts')
        try:
            with open('/etc/rhsm/facts/leapp.facts', 'w') as f:
                json.dump(_flattened({
                    'leapp': [
                        activity for activity in activities
                        if activity.get('activity', '') in ('preupgrade', 'upgrade')]
                    }), f, indent=4)
            self._commit_rhsm_facts()
        except OSError:
            # We don't care about failing to 'create' the file here
            # even though it shouldn't though, just ignore it
            pass

    def _commit_rhsm_facts(self):
        if runs_in_container():
            return
        cmd = ['/usr/sbin/subscription-manager', 'facts', '--update']
        try:
            _call(cmd, lambda x, y: None, lambda x, y: None)
        except (OSError, ValueError, TypeError):
            # We don't care about errors here, just ignore them
            pass

    def save(self):
        self._crumbs['run_id'] = os.environ.get('LEAPP_EXECUTION_ID', 'N/A')
        self._crumbs['leapp_file_changes'].extend(self._verify_leapp_pkgs())
        messages = get_messages(('IPUConfig',), self._crumbs['run_id'])
        versions = json.loads((messages or [{}])[0].get('message', {}).get(
            'data', '{}')).get('version', {'target': 'N/A', 'source': 'N/A'})
        self._crumbs['target_os'] = 'Red Hat Enterprise Linux {target}'.format(**versions)
        self._crumbs['source_os'] = 'Red Hat Enterprise Linux {source}'.format(**versions)
        self._crumbs['activity_ended'] = datetime.datetime.utcnow().isoformat() + 'Z'
        self._crumbs['env'] = {k: v for k, v in os.environ.items() if k.startswith('LEAPP_')}
        try:
            with open('/etc/migration-results', 'a+') as crumbs:
                crumbs.seek(0)
                doc = {'activities': []}
                try:
                    content = json.load(crumbs)
                    if isinstance(content, dict):
                        if isinstance(content.get('activities', None), list):
                            doc = content
                except JSONDecodeError:
                    # Expected to happen when /etc/migration-results is still empty or does not yet exist
                    pass
                doc['activities'].append(self._crumbs)
                crumbs.seek(0)
                crumbs.truncate()
                json.dump(doc, crumbs, indent=2, sort_keys=True)
                crumbs.write('\n')
                if os.environ.get('LEAPP_NO_RHSM_FACTS', '0') != '1':
                    self._save_rhsm_facts(doc['activities'])
        except OSError:
            sys.stderr.write('WARNING: Could not write to /etc/migration-results\n')

    def _get_packages(self):
        cmd = ['/bin/bash', '-c', 'rpm -qa --queryformat="%{nevra} %{SIGPGP:pgpsig}\n" | grep -Ee "leapp|snactor"']
        res = _call(cmd, lambda x, y: None, lambda x, y: None)
        if res.get('exit_code', None) == 0:
            if res.get('stdout', None):
                return [{'nevra': t[0], 'signature': t[1]}
                        for t in [line.strip().split(' ', 1) for line in res['stdout'].split('\n') if line.strip()]]
        return []

    def _verify_leapp_pkgs(self):
        if not os.environ.get('LEAPP_IPU_IN_PROGRESS'):
            return []
        upg_path = os.environ.get('LEAPP_IPU_IN_PROGRESS').split('to')
        cmd = ['/bin/bash', '-c', 'rpm -V leapp leapp-upgrade-el{}toel{}'.format(upg_path[0], upg_path[1])]
        res = _call(cmd, lambda x, y: None, lambda x, y: None)
        if res.get('exit_code', None) == 1:
            if res.get('stdout', None):
                return [{'result': t[0], 'file_name': t[1]}
                        for t in [line.strip().split(' ', 1) for line in res['stdout'].split('\n') if line.strip()]]
        return []


def produces_breadcrumbs(f):
    """
    Ensures that `/etc/migration-results` gets produced on every invocation of `leapp upgrade` & `leapp preupgrade`

    Every execution of the upgrade will have their own entry in the /etc/migration-results file.
    For a user flow like: leapp preupgrade && leapp upgrade && reboot there should be 5 new entries in the file:

    1. leapp preupgrade
    2. leapp upgrade (Source OS)
    3. leapp upgrade (Initram Phase - Until including RPM transaction)
    4. leapp upgrade (Initram Phase - Post RPM Transaction)
    5. leapp upgrade (Target OS - First Boot)

    Depending on future design changes of the IPU Worklow, the output may vary.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        breadcrumbs = _BreadCrumbs(activity=f.__name__)
        try:
            return f(*args, breadcrumbs=breadcrumbs, **kwargs)
        except SystemExit as e:
            if e.code != 0:
                breadcrumbs.fail()
            raise
        except BaseException:
            breadcrumbs.fail()
            raise
        finally:
            breadcrumbs.save()
    return wrapper
