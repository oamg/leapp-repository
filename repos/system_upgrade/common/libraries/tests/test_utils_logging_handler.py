# -*- coding: UTF-8 -*-
import os.path
import sys

from leapp.libraries.common.utils import config, logging_handler
from leapp.libraries.stdlib.call import STDERR, STDOUT


def test_logging_handler(capfdbinary, monkeypatch):
    debug_on = False
    monkeypatch.setattr(config, 'is_debug', lambda: debug_on)
    panagrams_path = os.path.join(os.path.dirname(__file__), 'panagrams')
    with open(panagrams_path, 'rb') as f:
        test_data = f.read()

    bin_test_data = test_data
    if isinstance(test_data, str) and str is not bytes:
        bin_test_data = test_data.encode()
    # Should not log anything
    for c in range(0, len(bin_test_data)):
        logging_handler((None, STDERR), bin_test_data[c:c+1])
    debug_on = True
    for c in range(0, len(bin_test_data)):
        logging_handler((None, STDERR), bin_test_data[c:c+1])
    for c in range(0, len(bin_test_data)):
        logging_handler((None, STDOUT), bin_test_data[c:c+1])
    captured = capfdbinary.readouterr()
    assert captured.out == bin_test_data
    assert captured.err == bin_test_data


def test_logging_handler_arrow(capfdbinary, monkeypatch):
    debug_on = False
    monkeypatch.setattr(config, 'is_debug', lambda: debug_on)
    # → => '\xe2\x86\x92'
    if sys.version_info > (3, 0):
        buf = b'\xe2\x86\x92'
    else:
        buf = '\xe2\x86\x92'

    for i in range(0, len(buf)):
        debug_on = False
        logging_handler((None, STDERR), buf[i:i+1])
        debug_on = True
        logging_handler((None, STDERR), buf[i:i+1])
        logging_handler((None, STDOUT), buf[i:i+1])
    captured = capfdbinary.readouterr()
    assert captured.err == buf
    assert captured.out == buf
