from configparser import InterpolationSyntaxError

import pytest

from leapp.libraries.common import utils


def test_parse_config_no_interpolation_preserves_url_encoding():
    """Values with URL-encoded sequences must be read literally (no % interpolation)."""
    cfg_text = (
        '[repo]\n'
        'name=test\n'
        'baseurl=https://example.com/path%20with%20spaces/repo%3Fquery=1\n'
    )
    parser = utils.parse_config(cfg_text, strict=False, no_interpolation=True)
    assert parser.get('repo', 'baseurl') == (
        'https://example.com/path%20with%20spaces/repo%3Fquery=1'
    )


def test_parse_config_interpolation_rejects_bare_percent_sequences():
    """Default ConfigParser treats '%' as interpolation; invalid sequences must raise."""
    cfg_text = (
        '[repo]\n'
        'name=test\n'
        'baseurl=https://example.com/path%20with%20spaces/repo\n'
    )
    parser = utils.parse_config(cfg_text, strict=False, no_interpolation=False)
    with pytest.raises(InterpolationSyntaxError):
        parser.get('repo', 'baseurl')
