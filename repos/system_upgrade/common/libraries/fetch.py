import io  # Python2/Python3 compatible IO (open etc.)
import json
import os

import requests

from leapp import models
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_consumed_data_stream_id, get_env
from leapp.libraries.common.rpms import get_leapp_packages, LeappComponents
from leapp.libraries.stdlib import api

SERVICE_HOST_DEFAULT = "https://cert.cloud.redhat.com"
REQUEST_TIMEOUT = (5, 30)
MAX_ATTEMPTS = 3
ASSET_PROVIDED_DATA_STREAMS_FIELD = 'provided_data_streams'


def _get_hint(local_path):
    hint = (
        'All official data files are part of the installed rpms these days.'
        ' The rpm is the only official source of the official data files for in-place upgrades.'
        ' This issue is usually encountered when the data files are incorrectly customized, replaced, or removed'
        ' (e.g. by custom scripts).'
        ' In case you want to recover the original {lp} file, remove the current one (if it still exists)'
        ' and reinstall the following packages: {rpms}.'
        .format(
            lp=local_path,
            rpms=', '.join(get_leapp_packages(component=LeappComponents.REPOSITORY))
        )
    )
    return hint


def _raise_error(local_path, details):
    """
    If the file acquisition fails in any way, throw an informative error to stop the actor.
    """
    summary = 'Data file {lp} is missing or invalid.'.format(lp=local_path)

    raise StopActorExecutionError(summary, details={'details': details, 'hint': _get_hint(local_path)})


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


def read_or_fetch(filename,
                  directory="/etc/leapp/files",
                  service=None,
                  allow_empty=False,
                  encoding='utf-8',
                  data_stream=None,
                  allow_download=True):
    """
    Return the contents of a text file or fetch them from an online service if the file does not exist.

    :param str filename: The name of the file to read or fetch.
    :param str directory: Directory that should contain the file.
    :param str service: URL to the service providing the data if the file is missing.
    :param Optional[str] with_leapp_version: Inject the given leapp version when fetching from a service.
    :param bool allow_empty: Raise an error if the resulting data are empty.
    :param str encoding: Encoding to use when decoding the raw binary data.
    :param bool allow_download: Allow the fallback to download the data file if not present.
    :returns: Text contents of the file. Text is decoded using the provided encoding.
    :rtype: str
    """
    logger = api.current_logger()
    local_path = os.path.join(directory, filename)

    # try to get the data locally
    if not os.path.exists(local_path):
        if not allow_download:
            _raise_error(local_path, "File {lp} does not exist.".format(lp=local_path))
        logger.warning("File {lp} does not exist, falling back to online service)".format(lp=local_path))
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
    if data_stream:
        service_path = "{s}/api/pes/{stream}/{f}".format(s=service, stream=data_stream, f=filename)
    else:
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


def load_data_asset(actor_requesting_asset,
                    asset_filename,
                    asset_fulltext_name,
                    docs_url,
                    docs_title):
    """
    Load the content of the data asset with given asset_filename
    and produce :class:`leapp.model.ConsumedDataAsset` message.

    :param Actor actor_requesting_asset: The actor instance requesting the asset file. It is necessary for the actor
                                         to be able to produce ConsumedDataAsset message in order for leapp to be able
                                         to uniformly report assets with incorrect versions.
    :param str asset_filename: The file name of the asset to load.
    :param str asset_fulltext_name: A human readable asset name to display in error messages.
    :param str docs_url: Docs url to provide if an asset is malformed or outdated.
    :param str docs_title: Title of the documentation to where `docs_url` points to.
    :returns: A dict with asset contents (a parsed JSON), or None if the asset was outdated.
    :raises StopActorExecutionError: In following cases:
        * ConsumedDataAsset is not specified in the produces tuple of the actor_requesting_asset actor
        * The content of the required data file is not valid JSON format
        * The required data cannot be obtained (e.g. due to missing file)
    """

    # Check that the actor that is attempting to obtain the asset meets the contract to call this function
    if models.ConsumedDataAsset not in actor_requesting_asset.produces:
        raise StopActorExecutionError('The supplied `actor_requesting_asset` does not produce ConsumedDataAsset.')

    if docs_url:
        error_hint = {'hint': ('Read documentation at the following link for more information about how to retrieve '
                               'the valid file: {0}'.format(docs_url))}
    else:
        error_hint = {'hint': _get_hint(os.path.join('/etc/leapp/files', asset_filename))}

    data_stream_id = get_consumed_data_stream_id()
    data_stream_major = data_stream_id.split('.', 1)[0]
    api.current_logger().info(
        'Attempting to load the asset {0} (data_stream={1})'.format(asset_filename, data_stream_id)
    )

    try:
        # The asset family ID has the form (major, minor), include only `major` in the URL
        raw_asset_contents = read_or_fetch(asset_filename, data_stream=data_stream_major, allow_download=False)
        asset_contents = json.loads(raw_asset_contents)
    except ValueError:
        msg = 'The {0} file (at {1}) does not contain a valid JSON object.'.format(asset_fulltext_name, asset_filename)
        raise StopActorExecutionError(msg, details=error_hint)

    if not isinstance(asset_contents, dict):
        # Should be unlikely
        msg = 'The {0} file (at {1}) is invalid - it does not contain a JSON object at the topmost level.'
        raise StopActorExecutionError(msg.format(asset_fulltext_name, asset_filename), details=error_hint)

    provided_data_streams = asset_contents.get(ASSET_PROVIDED_DATA_STREAMS_FIELD)
    if provided_data_streams and not isinstance(provided_data_streams, list):
        provided_data_streams = []  # The asset will be later reported as malformed

    api.produce(models.ConsumedDataAsset(filename=asset_filename,
                                         fulltext_name=asset_fulltext_name,
                                         docs_url=docs_url,
                                         docs_title=docs_title,
                                         provided_data_streams=provided_data_streams))

    return asset_contents
