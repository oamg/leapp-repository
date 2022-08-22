import io  # Python2/Python3 compatible IO (open etc.)
import os

import requests

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api

SERVICE_HOST_DEFAULT = "https://cert.cloud.redhat.com"
REQUEST_TIMEOUT = (5, 30)
MAX_ATTEMPTS = 3


def _raise_error(local_path, details):
    """
    If the file acquisition fails in any way, throw an informative error to stop the actor.
    """
    summary = "Data file {lp} is invalid or could not be retrieved.".format(lp=local_path)
    hint = ("Read documentation at: https://access.redhat.com/articles/3664871"
            " for more information about how to retrieve the file.")

    raise StopActorExecutionError(summary, details={'details': details, 'hint': hint})


def _request_data(service_path, cert, proxies, timeout=REQUEST_TIMEOUT):
    logger = api.current_logger()
    attempt = 0
    while True:
        attempt += 1
        try:
            return requests.get(service_path, cert=cert, proxies=proxies, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout as e:
            etype_msg = 'Connection timeout'
            if isinstance(e, requests.exceptions.ReadTimeout):
                etype_msg = 'Read timeout'
                # reading is slow, increase the time limit for the reading
                timeout = (timeout[0], timeout[1] + 10)
            if attempt > MAX_ATTEMPTS:
                logger.warning(
                    'Attempt {} of {} to get {} failed: {}.'
                    .format(MAX_ATTEMPTS, MAX_ATTEMPTS, service_path, etype_msg)
                )
                raise

            logger.info(
                'Attempt {} of {} to get {} failed: {}. Retrying...'
                .format(attempt, MAX_ATTEMPTS, service_path, etype_msg)
            )


def read_or_fetch(filename, directory="/etc/leapp/files", service=None, allow_empty=False, encoding='utf-8'):
    """
    Return the contents of a text file or fetch them from an online service if the file does not exist.

    :param str filename: The name of the file to read or fetch.
    :param str directory: Directory that should contain the file.
    :param str service: URL to the service providing the data if the file is missing.
    :param bool allow_empty: Raise an error if the resulting data are empty.
    :param str encoding: Encoding to use when decoding the raw binary data.
    :returns: Text contents of the file. Text is decoded using the provided encoding.
    :rtype: str
    """
    logger = api.current_logger()
    local_path = os.path.join(directory, filename)

    # try to get the data locally
    if not os.path.exists(local_path):
        logger.warning("File {lp} does not exist, falling back to online service".format(lp=local_path))
    else:
        try:
            with io.open(local_path, encoding=encoding) as f:
                data = f.read()
                if not allow_empty and not data:
                    _raise_error(local_path, "File {lp} exists but is empty".format(lp=local_path))
                logger.warning("File {lp} successfully read ({l} bytes)".format(lp=local_path, l=len(data)))
                return data
        except EnvironmentError:
            _raise_error(local_path, "File {lp} exists but couldn't be read".format(lp=local_path))
        except Exception as e:
            raise e

    # if the data is not present locally, fetch it from the online service
    service = service or get_env("LEAPP_SERVICE_HOST", default=SERVICE_HOST_DEFAULT)
    service_path = "{s}/api/pes/{f}".format(s=service, f=filename)
    proxy = get_env("LEAPP_PROXY_HOST")
    proxies = {"https": proxy} if proxy else None
    cert = ("/etc/pki/consumer/cert.pem", "/etc/pki/consumer/key.pem")
    response = None
    try:
        response = _request_data(service_path, cert=cert, proxies=proxies)
    except requests.exceptions.RequestException as e:
        logger.error(e)
        _raise_error(local_path, "Could not fetch {f} from {sp} (unreachable address).".format(
            f=filename, sp=service_path))
    # almost certainly missing certs
    except (OSError, IOError) as e:
        logger.error(e)
        _raise_error(local_path, ("Could not fetch {f} from {sp} (missing certificates). Is the machine"
                                  " registered?".format(f=filename, sp=service_path)))
    if response.status_code != 200:
        _raise_error(local_path, "Could not fetch {f} from {sp} (error code: {e}).".format(
            f=filename, sp=service_path, e=response.status_code))

    if not allow_empty and not response.content:
        _raise_error(local_path, "File {lp} successfully retrieved but it's empty".format(lp=local_path))
    logger.warning("File {sp} successfully retrieved and read ({l} bytes)".format(
        sp=service_path, l=len(response.content)))

    return response.content.decode(encoding)
