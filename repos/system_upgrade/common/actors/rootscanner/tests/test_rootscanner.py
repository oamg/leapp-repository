# -*- coding: utf-8 -*-
import os
import shutil
import tempfile

import pytest

from leapp.libraries.actor.rootscanner import scan_dir


@pytest.mark.parametrize("filename,symlink,count_invalid",
                         [('a_utf_file'.encode('utf-8'), "utf8_symlink".encode('utf-8'), 0),
                          ('простофайл'.encode('koi8-r'), "этонеутф8".encode('koi8-r'), 2),
                          ('a_utf_file'.encode('utf-8'), "этонеутф8".encode('koi8-r'), 1)])
def test_invalid_symlinks(filename, symlink, count_invalid):
    # Let's create a directory with both valid utf-8 and non-utf symlinks
    # NOTE(ivasilev) As this has to run for python2 as well can't use the nice tempfile.TemporaryDirectory way
    tmpdirname = tempfile.mkdtemp()
    # create the file in the temp directory
    path_to_file = os.path.join(tmpdirname.encode('utf-8'), filename)
    path_to_symlink = os.path.join(tmpdirname.encode('utf-8'), symlink)
    with open(path_to_file, 'w') as f:
        f.write('Some data here')
    # create a symlink
    os.symlink(path_to_file, path_to_symlink)
    # run scan_dir
    model = scan_dir(tmpdirname.encode('utf-8'))
    # verify the results
    assert len(model.items) == 2 - count_invalid
    assert len(model.invalid_items) == count_invalid
    # cleanup
    shutil.rmtree(tmpdirname)
