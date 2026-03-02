import pytest

from leapp.libraries.actor.add_provider import (
    _add_lines,
    _append,
    _get_leapp_comment,
    _modify_file,
    _replace,
    APPEND_STRING,
    NotFoundException
)
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api

testdata = (
    ([], 'one', ['one\n']),
    (['first'], 'one', ['first', 'one\n']),
    (['first'], 'one\ntwo', ['first', 'one\n', 'two\n']),
)


@pytest.mark.parametrize('lines,add,expected', testdata)
def test_add_lines(lines, add, expected):
    r = _add_lines(lines, add)
    assert r == expected


testdata = (
    ([], "search", "replace", None, False, None),
    ([], "search", "replace", "comment", False, None),
    ([], r"\s*", "replace", None, False, None),
    ([], r"\s*", "replace", "comment", False, None),
    (["text"], "text", "replace", None, False, ["replace\n"]),
    (["text"], "text", "replace", "comment", False, ["comment", "replace\n"]),
    (["text"], "text", "replace", "comment", True, ["comment", "# text", "replace\n"]),
    (["text    "], "text", "replace", "comment", True, ["comment", "# text    ", "replace\n"]),
    (["    text"], "text", "replace", "comment", True, ["comment", "#     text", "replace\n"]),
    (["text    text"], r"text\s*text", "replace", "comment", True, ["comment", "# text    text", "replace\n"]),
    (["first", "text", "last"], "text", "replace", "comment", True,
     ["first", "comment", "# text", "replace\n", "last"]),
)


@pytest.mark.parametrize('lines,search,replace,comment,backup,expected', testdata)
def test_replace(lines, search, replace, comment, backup, expected):
    try:
        r = _replace(lines, search, replace, comment, backup)
        if expected:
            assert r == expected
        else:
            assert False
    except NotFoundException:
        assert not expected


testdata = (
    ([], 'one', 'comment', ['comment', 'one\n']),
    (['first'], 'one', 'comment', ['first', 'comment', 'one\n']),
    (['first'], 'one\ntwo', 'comment', ['first', 'comment', 'one\n', 'two\n']),
)


@pytest.mark.parametrize('lines,add,comment,expected', testdata)
def test_append(lines, add, comment, expected):
    r = _append(lines, add, comment)
    assert r == expected


class MockFile:
    def __init__(self, content=None):
        self.content = content
        self.error = False

    def readlines(self):
        return self.content.splitlines(True)

    def seek(self, n):
        self.content = ''

    def write(self, content):
        self.content = content


testdata = (
    ("", ""),
    (
        "openssl_conf=default_modules\n",
        "{c}# openssl_conf=default_modules\nopenssl_conf = openssl_init\n",
    ),
    (
        "openssl_conf = default_modules\n",
        "{c}# openssl_conf = default_modules\nopenssl_conf = openssl_init\n",
    ),
    (
        "openssl_conf  =  default_modules\n",
        "{c}# openssl_conf  =  default_modules\nopenssl_conf = openssl_init\n",
    ),
    (
        "  openssl_conf = default_modules  \n",
        "{c}#   openssl_conf = default_modules  \nopenssl_conf = openssl_init\n",
    ),
    (
        "[default_modules]\n",
        "{c}# [default_modules]\n[openssl_init]\nproviders = provider_sect\n",
    ),
    (
        "[  default_modules  ]\n",
        "{c}# [  default_modules  ]\n[openssl_init]\nproviders = provider_sect\n",
    ),
    (
        "  [ default_modules ] \n",
        "{c}#   [ default_modules ] \n[openssl_init]\nproviders = provider_sect\n",
    ),
    (
        "openssl_conf=default_modules\n[default_modules]\n",
        "{c}# openssl_conf=default_modules\nopenssl_conf = openssl_init\n"
        "{c}# [default_modules]\n[openssl_init]\nproviders = provider_sect\n",
    ),
)


@pytest.mark.parametrize('file_content,expected', testdata)
def test_modify_file(monkeypatch, file_content, expected):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    f = MockFile(file_content.format(c=_get_leapp_comment()))

    # Test separate replaces and do not fail if pattern is not found
    _modify_file(f, False)

    assert f.content == "{}{}{}\n".format(
        expected.format(c=_get_leapp_comment()), _get_leapp_comment(), APPEND_STRING
    )
