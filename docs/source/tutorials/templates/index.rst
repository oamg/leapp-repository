Templates
=========

Here you can find out various templates (examples) of actors that are covering
some common situations that people want to deal with during in-place upgrades.
Templates contains usually comments with additional explanations providing clues
what people want to do most likely in particular actors. Sometimes you will
want to possibly look at several templates and mix them to get you solution.

Our goal is to provide hints to people how they could create some actors
to cover some typical scenarios. Note that templates can be updated over time
as overall in-place upgrade solution is changed. So it's good to check
documentation for the particular leapp-repository version you have installed
on the system (do not exchange the version of leapp-repository with leapp!). E.g.:

Note these templates do not meet best practices for the actor development in
the official **leapp-repository** repository - to keep them short and simple.

```bash
rpm -qa "leapp-upgrade*"
```

       TODO: make a link to best practices documentation.

.. toctree::
    :maxdepth: 4
    :caption: Contents:
    :glob:

    add-kernel-driver
    execute-custom-script

.. Indices and tables
.. ==================
..
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
