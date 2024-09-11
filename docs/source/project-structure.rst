Project structure
=================

The **Leapp Project** provides the framework for automating in-place upgrades from one major version of Red Hat Enterprise Linux to another. It is organized into a set of modular components, each responsible for specific tasks during the upgrade process. These components are managed across multiple **repos**, logically grouped to facilitate upgrades between different RHEL paths.

This documentation explains the structure of the **Leapp repository** and provides guidance on how to determine where to place new entities, such as actors, models, and libraries, within the project.

.. toctree::
    :maxdepth: 4
    :caption: Contents:
    :glob:

    repositories
    data
    cli

.. Indices and tables
.. ==================
..
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
