#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import types

import sequences

import logging
logging.basicConfig()
LOG = logging.getLogger(__name__)


class Test_filestructure(unittest.TestCase):
    def test_mod(self):
        # Basic test to make sure module was imported
        self.assertEqual(type(sequences), types.ModuleType)

    def test_fileStructure(self):
        instance = sequences.utils.fileStructure.FilestructurePath.from_path("SG://Path/That/Doesnt/Exist.jpg")
        assert isinstance(instance, sequences.utils.fileStructure.FilestructurePath)

    def test_perforcePath(self):
        path = None
        try:
            p4 = sequences.utils.perforce.newInstance()
        except Exception, e:
            # No P4 Can't Test
            LOG.warning(e)
            return

        # Find a depot with a client
        depots = sequences.utils.perforce.get_depot_paths(p4=p4)
        for depot in depots:
            depot = depot + '/'
            try:
                client = sequences.utils.perforce.get_client_from_path(p4, depot)
                if client:
                    path = depot
                    break
                else:
                    depot = depot + '/main'
                    client = sequences.utils.perforce.get_client_from_path(p4, depot)
                    if client:
                        path = depot
                        break
            except Exception:
                continue

        if not path:
            # No valid P4 Path could be found for testing, setup must be to different
            LOG.warning("Couldn't test P4 - No Clients Found")
            return

        instance = sequences.utils.fileStructure.PerforcePath.from_path(path)
        assert isinstance(instance, (sequences.utils.fileStructure.PerforcePath, sequences.utils.fileStructure.FilestructurePath))

    def test_diskPath(self):
        # Just use a root path based on OS that we know exists to test with
        _os = sequences.utils.get_os()
        if _os == 'mac':
            path = '/Applications'
        elif _os == 'windows':
            path = 'C:/Windows'
        else:
            path = '/tmp'
        instance = sequences.utils.fileStructure.FilestructurePath.from_path(path)
        assert isinstance(instance, sequences.utils.fileStructure.DiskPath)

if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
