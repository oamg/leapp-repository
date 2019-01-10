# Contributing guidelines for writing actors

In addition to the [Leapp project contribution guidelines](https://github.com/oamg/leapp-guidelines/blob/master/contributing-guidelines.rst), please follow also these rules:

1. Description of all PRs must clearly state what is being changed and the rationale for the change.
1. Description in the docstring of actors, models and/or phases must conform to their implementation. Description of an actor should include the expected behaviour, inputs and outputs, so that one is able to write [component tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md#component-tests) for the actor without looking at the actor's code.
1. Actors must have [component tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md#component-tests) covering the behaviour mentioned in the actor's description.
1. Bug fix PRs must include [component tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md#component-tests) covering the fixed issue.
1. Writing [unit tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md#unit-tests) for the actor's code is optional but encouraged.
1. Follow [PEP 8 - Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
   - with the exception of line length which can be up to 120 characters
   - use of linters (PyLint, pep8, flake8) is encouraged to be sure to follow the PEP 8
1. Follow [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257)
1. All Python code must be Python 2.7+/3.6+ compatible.
1. New folders and/or Python files must use lowercase without underscores.
   - with the exception of test file names, which need to be named `test_*.py` or `*_test.py`
1. Do not use _actor_ in the actor's name, neither _model/topic/tag/phase_ in the model/topic/tag/phase name, as these things are implicit.
1. The actor's main file must be named `actor.py`.
1. Use of Python language for the actor's logic is preferred, even though you can call a script in any language from the actor's Python skeleton.
1. The code should follow these documents as much as feasible:
   - the [Leapp project Python coding guidelines](https://github.com/oamg/leapp-guidelines/blob/master/python-coding-guidelines.md).
   - the [Best practices for writing actors](https://github.com/oamg/leapp-repository/blob/master/docs/best-practices.md)
