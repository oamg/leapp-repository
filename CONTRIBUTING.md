# Contribution guidelines for writing actors

These guidelines are an addition to the [Leapp project contribution guidelines](https://github.com/oamg/leapp-guidelines/blob/master/contributing-guidelines.rst).

## Coding guidelines

1. The code should follow these documents as much as feasible:
   - the [Leapp project Python coding guidelines](https://github.com/oamg/leapp-guidelines/blob/master/python-coding-guidelines.md).
   - the [Best practices for writing actors](https://github.com/oamg/leapp-repository/blob/master/docs/best-practices.md)
1. All Python code must be Python 2.7+/3.6+ compatible.
1. Use of Python language for the actor's logic is **preferred**, even though you can call a script in any language from the actor's Python skeleton.

## Tests

1. Actors must include [component or unit tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md).
1. Bug fix PRs must include [tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md) covering the fixed issue.

## Naming convention

1. New folders and/or Python files must use lowercase without underscores.
   - with the exception of test file names, which need to be named `test_*.py` or `*_test.py`
1. Do not use _actor_ in the actor's name, neither _model/topic/tag/phase_ in the model/topic/tag/phase name, as these things are implicit.
1. The actor's main file must be named `actor.py`.

## Code style

1. Follow [PEP 8 - Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
   - with the exception of line length which can be up to 120 characters
   - use of linters (PyLint, pep8, flake8) is encouraged
1. String and docstring convention
   - Follow [PEP 257 - Docstring Conventions](https://www.python.org/dev/peps/pep-0257)
      - with the exception, that the summary line of a multi-line docstring shall be on a new line, not on the same line as the opening quotes.
   - Description in the docstring of actors, models and/or phases must conform to their implementation. Description of an actor should include the expected behaviour and inputs/outputs, so that one is able to write [component tests](https://github.com/oamg/leapp-repository/blob/master/docs/tests.md#component-tests) for the actor without looking at the actor's code.
   - <details>
       <summary>Click for the example of how to write strings and docstrings</summary>
  
        ```python
        class MyActor(Actor):
            """
            Start with a single-line brief summary of the actor (under the triple quotes).

            Leave a blank line below the summary and then describe the actor's behaviour
            here in detail.
            """
            name = 'my_actor'

            def process(self):
                """This is a simple method."""
                complicated_method(True)

            def complicated_method(switch):
                """
                This is a summary line of a more complicated method.

                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc porta sed
                urna venenatis faucibus. Phasellus at bibendum ligula, a posuere metus.

                :param switch: Description of the parameter.
                :type switch: Expected type of the parameter.
                :return: Description of what the method returns
                """
                mutliline_string = (
                    'I am a multiline string.\n'
                    'This is my second line.'
                )
                return mutliline_string
        ```
      </details>