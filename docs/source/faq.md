# Frequently Asked Questions

```{contents}
:local:
```

## Why is the leapp-repository project separated from Leapp?

It's similar relationship as you can find between Ansible and ansible playbooks.
Having Ansible does not mean that it configure all systems as people want.
People have to create playbooks to define how systems should be configured.

With leapp and leapp-repository it's same. The leapp project covers only the
Leapp framework, the leapp tool (providing CLI), and snactor - the utility helping
with the development and testing. The framework has been supposed to be used
for multiple purposes. In-Place Upgrades have been just one of them.

Even when we work on both projects, having the work on framework separated
from leapp repositories containing number of actors simplifies the maintenance
of the project.

## What is an actor and what does it do?

An {py:class}`~leapp.actors.Actor` in the realm of the Leapp project is a step that is executed within a workflow. Actors define what kind of data they expect and what kind of data they produce.

One of the use cases for actors is to scan the system and provide the discoveries to other actors through messages. Other actors consume these messages to make decisions, apply changes to the system, or process the information to produce new messages.

## When and why do I need to write an actor?

This project is focused on in-place upgrades between major versions of RHEL systems.
Here we can implement and test solutions with the focus on content of the particular
distribution (RPM signed by GPG keys connected to the distribution). However,
most of the time you do not install just RPMs from that particular system, but
also your custom or third-party SW - or HW also. When you need to handle
your custom/third-party stuff, you will need to possibly create custom actors
to do so - or you could ask a third-party vendor for a solution.

Also, in case you have a specific system setup that we cannot cover, you would
possibly customize the upgrade on your systems.

## What are the best practices for writing actors for in-place upgrades?

Read the [Best practices for writing actors](best-practices).

## What are the best practices for creating and adding custom actors for in-place upgrades?

TBA

## What are the requirements for actors to be accepted by upstream?

It should follow the [Contribution guidelines](contributing) and the [Best practices for writing actors](best-practices) as much as feasible.
If you are not sure whether the solution you are thinking about will be accepted
at all, try to ask first via [Discussion](https://github.com/oamg/leapp-repository/discussions)
and discuss it with us.

## How can I debug my actor? Is there a standard/supported way how to log and get logs from actors/channels?

You can run your actor using the snactor tool and printing the output. [See the tutorial](tutorials/first-actor) on how to use snactor.

## Are there some technical limitations for an actor? Like maximum time execution, ...

There are no technical limitations but rather conceptual:

- Libraries to use:
  - See the section about actor dependencies in the [Best practices document](best-practices.md#do-not-introduce-new-dependencies)

Execution time:

- Some Red Hat customers do business in fields where time matters a lot. They may have obligations to not allow more than a few minutes of downtime per year. It means that we should make sure that our tooling causes as short downtime as possible.
- It's not currently possible to tell the Leapp framework that the actor takes longer time to execute.

## Are there some actions that are either forbidden or not recommended to be done in actors?

There are several, covered also in contribution guideline, but highlight these few:
1. **Do not alter the system in any way during so called preupgrade phases.**
Even then we want to postpone as many changes as possible after the `LateTestsPhase`
phase. Any deviation from this rule must be well justified.

1. **Do not use {py:mod}`subprocess` python module**. If you need to execute a shell command,
use the {py:func}`leapp.libraries.stdlib.run` function instead.

1. **Do not interact with the system during the `ChecksPhase`.** You can scan
the system in previous phase and generate a leapp message for the check actor.

## I got an error about PES data/ Repositories mapping.

Most likely you replaced leapp data files included in the installed RPM by
different files (usually by their obsolete versions). Remove them, reinstall
the package, and try to not replace them again. If it is not that case, contact
vendor of the package for support.

Note that in public space there are number of various versions of these files
and we are responsible only for files that we distribute together with our code.

