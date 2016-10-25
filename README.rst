===============================
Sequences
===============================


Matches and provides various functionality for strings and paths that contain sequence numbers. Allows for things like finding the first, last, next, or middle item in a sequence. Allows for renaming file sequences.


Installation
============

::

    pip install sequences

Documentation
=============

http://talesfrompipeline.com/docs/sequences/index.html


Development
===========

To set up `sequences` for local development:

1. Clone the repo locally::

    cd ~/dev
    git clone https://github.com/burninghelix123/sequences.git

2. Switch into the environment you want to test in::

    source /tools/maya/bin/activate

3. Install the module in development mode

    make dev


Use the `make` for a reference of the available development tools in this project.


Tips
----

To run a subset of tests::

    tox -e envname -- py.test -k test_myfeature

To run all the test environments in *parallel* (you need to ``pip install detox``)::

    detox
