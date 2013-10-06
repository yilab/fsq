===
FSQ
===

fsq is a standard for implementing queueing structures in POSIX file-systems.
fsq provides a standard for both directory layouts and work-item naming, which
allow for idempotent work-item construction, atomic enqueueing, and atomic
completion.

The fsq python library (``import fsq``) provides a programattic way to
enqueue, scan, introspect and manipulate queues from Python.

The fsq program provides mechanisms for enqueueing, scanning, introspecting,
auditing and repairing queues from the command line.

For more on the fsq standard see ``man 7 fsq``, for more on the fsq program
see ``man 1 fsq``.

Installing
==========

The fsq project lives on github_, and is available via pip_.

.. _github: https://github.com/axialmarket/fsq
.. _pip: https://pypi.python.org/pypi?:action=display&name=fsq

Installing v0.2.3 From Pip
--------------------------

::

    sudo pip install fsq==0.2.3

Installing v0.2.3 From Source
-----------------------------

::

    curl https://github.com/axialmarket/fsq/archive/version_0.2.3.tar.gz | tar vzxf -
    cd fsq
    sudo python setup.py install

Quick Overview
==============

Installing Queues
-----------------

To install a queue, simply run::

    $ fsq install a_queue

Or via the Python API::

    >>> import fsq
    >>> fsq.install(a_queue)

Installing a queue will create a directory in ``FSQ_ROOT`` (``/var/fsq/``)::

    /var/fsq/a_queue
    ├── done
    ├── fail
    ├── queue
    └── tmp

Enqueueing Work
---------------

To enqueue work to the ``a_queue`` queue, simply run::

    $ echo "data" | fsq enqueue a_queue args to enqueue

Or from the Python API::

    >>> import fsq
    >>> # enqueue a string
    >>> fsq.senqueue('a_queue', 'data', 'args', 'to', 'enqueue')
    >>> # ... or a file
    >>> fsq.senqueue('a_queue', '/path/to/data.file', 'args', 'to', 'enqueue')

Enqueueing adds a file to the ``queue`` directory of ``a_queue``::

    /var/fsq/a_queue
    ├── done
    ├── fail
    ├── queue
    |   └── _20131005205643_0_25577_mss_0_args_to_enqueue
    └── tmp

Processing Work
---------------

To process jobs, use the ``fsq scan`` program::

    $ # echo gets "args", "to", "enqueue" as $1..$3 and "data" on stdin
    $ fsq scan a_queue echo
    args to enqueue

Or from the Python API::

    >>> import fsq
    >>> for work in fsq.scan('a_queue'):
    ...     print " ".join(work.arguments)
    ...     fsq.done('a_queue')
    args to enqueue

Work that is successfully completed moves to the done directory::

    /var/fsq/a_queue
    ├── done
    |   └── _20131005205643_0_25577_mss_0_args_to_enqueue
    ├── fail
    ├── queue
    └── tmp

As fsq scans each work item, it obtains an exclusive lock on the work item
file, so it is safe to run multiple scan processes (or threads) in parallel on
the same queue with no fear of duplicating effort.

Failures in Processing Work
---------------------------

Should work fail during processing::

    $ fsq scan a_queue sh -c 'exit 100'

Or from the Python API::

    >>> import fsq
    >>> for work in fsq.scan('a_queue'):
    ...     fsq.fail('a_queue')

The failed work will be moved to the fail directory::

    /var/fsq/a_queue
    ├── done
    ├── fail
    |   └── _20131005205643_0_25577_mss_0_args_to_enqueue
    ├── queue
    └── tmp

Work can also fail temporarily, which will cause the work to remain in the
``queue`` directory until it is older than ``FSQ_TTL`` seconds old, or until
it has been tried more than ``FSQ_MAX_TRIES`` times unsuccessfully::

    $ # exit code 111 indicates temporary failure
    $ FSQ_MAX_TRIES=2 fsq scan a_queue sh -c 'exit 100'

Or from the Python API::

    >>> import fsq
    >>> fsq.set_const('FSQ_MAX_TRIES', 2)
    >>> for work in fsq.scan('a_queue'):
    ...     fsq.fail_tmp(work)

The name of the work item will change to indicate that the item has failed
once::

    /var/fsq/a_queue
    ├── done
    ├── fail
    ├── queue
    |   └── _20131005205643_0_25577_mss_1_args_to_enqueue
    └── tmp


Taking Queues Down
------------------

To temporaily stop all scanning of any queue, you simply use the ``fsq down``
program::

    $ fsq down a_queue

Or from the Python API::

    >>> import fsq
    >>> fsq.down('a_queue')

Which creates a regular file named ``down`` in the ``a_queue`` directory
preventing scan from working on the queue::

    /var/fsq/a_queue
    ├── done
    ├── down
    ├── fail
    ├── queue
    |   └── _20131005205643_0_25577_mss_0_args_to_enqueue
    └── tmp

To bring a queue back up again, you simply use the ``fsq up`` program::

    $ fsq up a_queue

Or from the Python API::

    >>> import fsq
    >>> fsq.up('a_queue')

Which removes the ``down`` file, and allows the queue to be scanned properly
again.

The tmp Directory
-----------------

The tmp directory within a_queue is used by fsq under the hood to ensure that
all items are enqueued atomically.

The fsq File Name
-----------------

::

    _20120710213904_0_13044_mss_0_args_to_enqueue
    _20120710213904_1_13044_mss_0_args_to_enqueue
    +|-----+------| + |-+-| |+| + |------+------|
    |      |        |   |    |  |        |
    |      |        |   |    |  |        +-> FSQ_DELIMITER seperated
    |      |        |   |    |  |            arguments
    |      |        |   |    |  +-> tries: number of failed attempts
    |      |        |   |    |      to process
    |      |        |   |    +-> hostname: the name of the host on
    |      |        |   |        which the work-item was enqueued.
    |      |        |   +-> pid of the process which enqueued the
    |      |        |       work-item
    |      |        +-> entropy: should a work-item be generated
    |      |            with the same arguments, pid, hostname
    |      |            and timestamp, entropy is incremented to
    |      |            generate uniqueness.
    |      +-> timestamp in FSQ_TIMEFMT format
    +-> FSQ_DELIMITER used at enqueue time

ENVIRONMENT
===========

The fsq suite and python library makes use of a number of environment
variables (each prefixed by ``FSQ_``), which modify its behavior.  Each
environment variable is also available as a package-level constant.

Please refer to ``man 7 fsq`` for a complete list.

AUTHORS
=======

| Matthew Story <matt.story@axial.net>
| Isaac (.ike) Levy <ike@blackskyresearch.net>
| Will O'Meara <will.omeara@axial.net>
| Jeff Rand <jeff.rand@axial.net>

With Additional Contributions From:

| Will Martino
| Will Slippey
| Jacob Yuan

And Thanks To:

| William Baxter (For trigger, and for inspiring fsq)
| Bruce Guenter (For nullmailer, featuring a simpler file-system queue)
| Daniel J Bernstein (For QMail, inspiring trigger and nullmailer)
