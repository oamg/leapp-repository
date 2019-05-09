**Before doing anything, please read
[Leapp framework documentation](https://leapp.readthedocs.io/).**

---

# How to write actors

See the tutorial for [creating the first actor](https://leapp.readthedocs.io/en/latest/first-actor.html).

# How to write actor tests

Please read documentation about [how to unit test actors](https://leapp.readthedocs.io/en/latest/unit-testing.html).

# How to install dependencies, run tests & execute actors

## Installing actor dependencies

Each actor can have its own Makefile with the `install-deps` target, which takes
care of installing any actor dependencies.
If your actor has any dependencies, include them in the Makefile.

To install dependencies for all actors, run:

``` bash
$ make install-deps
```

## Running tests locally

To run all tests from leapp-actors, run the following code from
the `leapp-actors` directory:

``` bash
$ make test
```

It is also possible to generate a report in a JUnit XML format:

``` bash
$ make test REPORT=report.xml
```

## Registering Leapp repositories and executing actors

When you want to execute actor with

``` bash
$ snactor run my_actor
```

or run discover feature

``` bash
$ snactor discover
```

it is good idea to register everything in `repos` to avoid possible errors
with parsing repository metadata (**NOTE:** these errors can be sometimes
cryptic, but may look like: `missing attribute name in .leapp/info`, etc.)

```bash
$ make register
```

where `register` target will run `snactor repo find --path repos`
(you can verify if your repositories are registered in
`~/.config/leapp/repos.json`).

## Troubleshooting

### Where can I report an issue or RFE related to the framework or other actors?

- GitHub issues are preferred:
  - Leapp framework: [https://github.com/oamg/leapp/issues/new/choose](https://github.com/oamg/leapp/issues/new/choose)
  - Leapp actors: [https://github.com/oamg/leapp-repository/issues/new/choose](https://github.com/oamg/leapp-repository/issues/new/choose)

- When filing an issue, include:
  - Steps to reproduce the issue
  - *All files in /var/log/leapp*
  - */var/lib/leapp/leapp.db*
  - *journalctl*
  - If you want, you can optionally send anything else would you like to provide (e.g. storage info)

**For your convenience you can pack all logs with this command:**

`# tar -czf leapp-logs.tgz /var/log/leapp /var/lib/leapp/leapp.db`

Then you may attach only the `leapp-logs.tgz` file.

### Where can I seek help?
We’ll gladly answer your questions and lead you to through any troubles with the
actor development.

You can reach us at IRC: `#leapp` on freenode.
