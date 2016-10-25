import os
import unittest

import sequences

import logging
logging.basicConfig()
LOG = logging.getLogger(__name__)


SCRIPT_DIR = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(SCRIPT_DIR, r'fileSearch')


class TestAbstractSequence(unittest.TestCase):
    sequenceClass = sequences.AbstractSequence

    def test_invalidSequence(self):
        path = 'non_existant_file.txt'
        self.assertRaises(ValueError, self.sequenceClass, path)

    def test_invalidSequenceType(self):
        self.assertRaises(TypeError, self.sequenceClass, 2)

    def test_matches(self):
        seq = 'aaa010.00001'
        seq = self.sequenceClass(seq)
        self.assertTrue(len(seq._matches) == 1)
        self.assertTrue(seq._matches[0] == seq._primary_match)

    def test_formatType_nums(self):
        seqStr = 'aaa010.00001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.formatType, 'nums')

        seqStr = 'aaa010.00001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.formatType, 'nums')

    def test_formatType_pounds(self):
        seqStr = 'aaa010.#####'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.formatType, 'pounds')

        seqStr = 'aaa010.#####'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.formatType, 'pounds')

    def test_formatType_formatstring(self):
        seqStr = 'aaa010.{item:05d}'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.formatType, 'formatstring')

        seqStr = 'aaa010.{item:05d}'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.formatType, 'formatstring')

    def test_formatType_invalid_format_string(self):
        seq = 'aaa010.{someitem:05d}'
        self.assertRaises(ValueError, self.sequenceClass, seq)

    def test_formatType_percent(self):
        seqStr = 'aaa010.%05d'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.formatType, 'percent')

        seqStr = 'aaa010.%05d'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.formatType, 'percent')

    def test_formatType_regex(self):
        seqStr = 'aaa010.\d{3}'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.formatType, 'regex')

        seqStr = 'aaa010.\d{3}'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.formatType, 'regex')

    def test_currentItem(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.currentItem, '0001')
        seq = 'aaa010.%05d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.currentItem, '%05d')

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.currentItem, '0001')

        seq = 'aaa010.%05d'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.currentItem, '%05d')

    def test_prefix(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.prefix, 'aaa010.')

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.prefix, 'aaa010.')

        seqStr = '0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.prefix, '')

    def test_num_different_sequence(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertRaises(ValueError, seq.num, 'aaa020.0002')

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertRaises(ValueError, seq.num, 'aaa020.0002')

    def test_num_missing_number(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertRaises(ValueError, seq.num, 'aaa020')

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertRaises(ValueError, seq.num, 'aaa020')

    def test_num_incorrect_padding(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        part = seq.is_part_of_sequence('aaa010.000001')
        self.assertFalse(part)

    def test_currentItemNumber(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.currentItemNumber, 1)
        seqStr = 'aaa010.%05d'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.currentItemNumber, None)
        seqStr = 'aaa010.#####'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.currentItemNumber, None)
        # Skip Validation
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.currentItemNumber, 1)

    def test_set_currentItemNumber(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.currentItemNumber, 1)
        seq.currentItemNumber = 2
        self.assertEqual(seq.currentItemNumber, 2)
        seq = 'aaa010.#####'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.currentItemNumber, None)
        seq.currentItemNumber = 2
        self.assertEqual(seq.currentItemNumber, 2)
        self.assertEqual(seq.currentItem, '00002')

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)

        def currentItemNumberSetter():
            seq.currentItemNumber = 'bb'

        self.assertRaises(TypeError, currentItemNumberSetter)

    def test_padding(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.padding, 4)
        seq = 'aaa010.%05d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.padding, 5)
        seq = 'aaa010.######'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.padding, 6)
        seq = 'aaa010.{item:05d}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.padding, 5)
        seq = 'aaa010.\d{2}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.padding, 2)

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.padding, 4)

    def test_get_string(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_string(2), 'aaa010.0002')
        self.assertEqual(seq.get_string(3, padding=2), 'aaa010.03')

        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.get_string(2), 'aaa010.0002')

    def test_get_pound_string(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(), 'aaa010.####')
        seq = 'aaa010.###'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(), 'aaa010.###')
        seq = 'aaa010.%06d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(), 'aaa010.######')
        seq = 'aaa010.{item:02d}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(), 'aaa010.##')
        seq = 'aaa010.\d{3}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(), 'aaa010.###')
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.get_pound_string(), 'aaa010.####')

    def test_get_pound_string_custom_padding(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_pound_string(padding=2), 'aaa010.##')

    def test_get_format_string(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:04d}')
        seq = 'aaa010.###'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:03d}')
        seq = 'aaa010.%06d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:06d}')
        seq = 'aaa010.{item:02d}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:02d}')
        seq = 'aaa010.\d{3}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:03d}')

        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.get_format_string(), 'aaa010.{item:04d}')

    def test_get_format_string_custom_padding(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(padding=3), 'aaa010.{item:03d}')

    def test_get_format_string_custom_formatKey(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_format_string(formatKey='myKey'), 'aaa010.{myKey:04d}')

    def test_get_percent_string(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%04d')
        seq = 'aaa010.###'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%03d')
        seq = 'aaa010.%06d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%06d')
        seq = 'aaa010.{item:02d}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%02d')
        seq = 'aaa010.\d{3}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%03d')

        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.get_percent_string(), 'aaa010.%04d')

    def test_get_percent_string_custom_padding(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_percent_string(padding=3), 'aaa010.%03d')

    def test_get_regex_string(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{4}')
        seq = 'aaa010.###'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{3}')
        seq = 'aaa010.%06d'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{6}')
        seq = 'aaa010.{item:02d}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{2}')
        seq = 'aaa010.\d{3}'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{3}')

        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq, skipValidate=True)
        self.assertEqual(seq.get_regex_string(), 'aaa010.\d{4}')

    def test_get_regex_string_custom_padding(self):
        seq = 'aaa010.0001'
        seq = self.sequenceClass(seq)
        self.assertEqual(seq.get_regex_string(padding=3), 'aaa010.\d{3}')

    def test_is_part_of_sequence(self):
        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.is_part_of_sequence('aaa020.0001'), False)
        self.assertEqual(seq.is_part_of_sequence('aaa020'), False)
        self.assertEqual(seq.is_part_of_sequence('aaa010.0001'), True)
        self.assertEqual(seq.is_part_of_sequence('aaa010.0002'), True)

        seqStr = 'aaa010.0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.is_part_of_sequence('aaa020.0001'), False)

    def test_get_next_item(self):
        seqStr = 'aaa010.0001'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.get_next_item(), 'aaa010.0002')
        seq.currentItemNumber = 1
        self.assertEqual(seq.get_next_item(), 'aaa010.0002')
        self.assertRaises(ValueError, seq.get_next_item, 4)
        self.assertEqual(seq.get_next_item(3), None)

        seqStr = 'aaa010.0001'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems, skipValidate=True)
        self.assertEqual(seq.get_next_item(), 'aaa010.0002')

    def test_get_previous_item(self):
        seqStr = 'aaa010.0001'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.get_previous_item(), None)
        seq.currentItemNumber = 2
        self.assertEqual(seq.get_previous_item(), 'aaa010.0001')

        seqStr = 'aaa010.0001'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems, skipValidate=True)
        self.assertEqual(seq.get_previous_item(), None)

    def test_sequence_items(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(len(seq.items), 3)
        self.assertEqual(seq.items[1], 'aaa010.0001')
        self.assertEqual(seq.items[3], 'aaa010.0003')

        # Skip Validation
        seq = self.sequenceClass(seqStr, seqStrItems, skipValidate=True)
        self.assertEqual(len(seq.items), 3)
        self.assertEqual(seq.items[1], 'aaa010.0001')
        self.assertEqual(seq.items[3], 'aaa010.0003')

    def test_getitem_slice(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq[1:3], seqStrItems)

    def test_numbers(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.numbers, [1, 2, 3])

    def test_numbers_sorting(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.numbers, [1, 2, 3])

    def test_built(self):
        # Look into what "built" is doing
        # seqStr = 'aaa010.####'
        pass

    def test_firstItem(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.firstItem, 'aaa010.0001')

        # test for empty []
        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.firstItem)

    def test_firstItemNumber(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.firstItemNumber, 1)

        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.firstItemNumber)

    def test_midItem(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.midItem, 'aaa010.0002')

        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.midItem)

    def test_midItemNumber(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.midItemNumber, 2)

        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.midItemNumber)

    def test_lastItem(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.lastItem, 'aaa010.0003')

        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.lastItem)

    def test_lastItemNumber(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.lastItemNumber, 3)

        seqStrItems = []
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertIsNone(seq.lastItemNumber)

    def test_range(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.range, [[1, 3]])

    def test_input_formats(self):
        seqStr = '0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.currentItemNumber, 1)
        seqStr = '0001.sequence'
        self.assertRaises(ValueError, self.sequenceClass, seqStr)
        seqStr = 'mySequence.0001.sequence'
        self.assertRaises(ValueError, self.sequenceClass, seqStr)

    def test_string(self):
        seqStr = '0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.string, seqStr)

    def test_suffix(self):
        seqStr = '0001'
        seq = self.sequenceClass(seqStr)
        self.assertEqual(seq.suffix, '')

        seqStr = '0001'
        seq = self.sequenceClass(seqStr, skipValidate=True)
        self.assertEqual(seq.suffix, '')


class TestBaseSequence(unittest.TestCase):
    sequenceClass = sequences.BaseSequence

    def test_invalidSequence(self):
        path = '/path/to/non_existant_file.txt'
        self.assertRaises(ValueError, self.sequenceClass, path)

    def test_delitem(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002', 'aaa010.0005', 'aaa010.0007']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(len(seq), 5)
        del seq[1]
        self.assertEqual(len(seq), 4)
        del seq[1:3]
        self.assertEqual(seq._sequence_items.items(), [(5, 'aaa010.0005'), (7, 'aaa010.0007')])

    def test_setitem(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        seq[4] = 'aaa010.0004'
        # print seq.items
        self.assertEqual(len(seq), 4)
        self.assertEqual(seq.lastItemNumber, 4)

    def test_setitem_invalid(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertRaises(ValueError, seq.__setitem__, 4, 'aaa020.0004')

    def test_keys(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq.numbers, [1, 2, 3])

    def test_clear(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        seq.clear()
        self.assertEqual(seq._sequence_items, {})

    def test_pop(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(len(seq), 3)
        result = seq.pop(3)
        self.assertEqual(result, 'aaa010.0003')
        self.assertEqual(len(seq), 2)

    def test_setdefault(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertRaises(ValueError, seq.setdefault, 4, 'aaa010.0003')

    def test_update(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0002']
        seq = self.sequenceClass(seqStr, seqStrItems)
        seqStrItems2 = ['aaa010.0004', 'aaa010.0005', 'aaa010.0006']
        seq2 = self.sequenceClass(seqStr, seqStrItems2)
        seq.update(seq2)
        self.assertEqual(len(seq), 6)

    def test_skipping(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0003', 'aaa010.0001', 'aaa010.0010']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(len(seq), 3)
        self.assertEqual(seq[3], 'aaa010.0003')
        self.assertEqual(seq[10], 'aaa010.0010')
        with self.assertRaises(KeyError):
            seq[2]

    def test_iterate(self):
        seqStr = 'aaa010.####'
        seqStrItems = ['aaa010.0001', 'aaa010.0002', 'aaa010.0003', 'aaa010.0004', 'aaa010.0005']
        seq = self.sequenceClass(seqStr, seqStrItems)
        self.assertEqual(seq[::2], ['aaa010.0001', 'aaa010.0003', 'aaa010.0005'])


class TestFileSequence(unittest.TestCase):
    sequenceClass = sequences.FileSequence

    def test_bad_path(self):
        path = '/path/to/non-existant-file'
        self.assertRaises(ValueError, sequences.FileSequence, path)

    def test_path(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        sequences.FileSequence(path)

    def test_normalize_path(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.FileSequence(path)
        self.assertEqual(seq.sourcePath, sequences.utils.path_normalize(path))

    def test_sequence_items_from_disk(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.FileSequence(path)
        self.assertEqual(len(seq), 3)

    def test_sequence_items_from_input(self):
        basePath = os.path.join(TEST_FILES_PATH, 'VersionSequence')
        seqItemPaths = [
            os.path.join(basePath, 'TestFile_v01.001.jpg'),
            os.path.join(basePath, 'TestFile_v01.002.jpg')
        ]
        seq = sequences.FileSequence.from_item_paths(seqItemPaths)
        self.assertEqual(len(seq), 2)

    def test_files(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        path = sequences.utils.path_normalize(path)
        seq = sequences.FileSequence(path)
        self.assertEqual(len(seq.files), 3)
        self.assertEqual(seq.files[0].path, path)

    def test_folder(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        folderPath = os.path.join(TEST_FILES_PATH, 'VersionSequence')
        folderPath = sequences.utils.path_normalize(folderPath)
        seq = sequences.FileSequence(path)
        self.assertEqual(seq.folder, folderPath)

    def test_ext(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.FileSequence(path)
        self.assertEqual(seq.ext, '.jpg')

        seq = sequences.FileSequence(path, skipValidate=True)
        self.assertEqual(seq.ext, '.jpg')

        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001')
        seq = sequences.FileSequence(path)
        self.assertEqual(seq.ext, '')

    def test_is_in_perforce(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.FileSequence(path, skipValidate=True)
        self.assertFalse(seq.isInPerforce(seq.sourceFile))


class TestImageSequence(unittest.TestCase):
    sequenceClass = sequences.ImageSequence

    def test_validate_ext(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        sequences.ImageSequence(path)
        path = os.path.join(TEST_FILES_PATH, 'Sequences', 'New Text Document_v01.0005.py')
        self.assertRaises(ValueError, sequences.ImageSequence, path)

    def test_currentFrameNumber(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.sourceNumber, 1)

    def test_firstFrame(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        path = sequences.utils.path_normalize(path)
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.firstPath, path)

    def test_firstFrameNumber(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.001.jpg')
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.firstNumber, 1)

    def test_lastFrame(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.003.jpg')
        path = sequences.utils.path_normalize(path)
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.lastPath, path)

    def test_lastFrameNumber(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.003.jpg')
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.lastNumber, 3)

    def test_frames(self):
        path = os.path.join(TEST_FILES_PATH, 'VersionSequence', 'TestFile_v01.003.jpg')
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.numbers, [1, 2, 3])
        path = os.path.join(TEST_FILES_PATH, 'Sequences', 'New Text Document_v01.0001.jpg')
        seq = sequences.ImageSequence(path)
        self.assertEqual(seq.numbers, [1, 10, 12, 13, 49, 80])


class TestSequenceUtils(unittest.TestCase):

    def test_flatten_sequences(self):
        results = []
        path = sequences.utils.join_paths(TEST_FILES_PATH, 'TestFlattening')
        folders = sequences.scan_for_files(path, groupFolders=True, recursive=True)
        for folder in folders:
            flattened = sequences.flatten_sequences(folder)
            for item in flattened:
                item = sequences.utils.path_normalize(item)
                framerange = sequences.get_sequence_range(item)
                results.append("{0} - {1}".format(item, framerange))

        test_results = [
            '/item1/v001/item1_v001.####.jpg - 1-6',
            '/item1/v002/item1_v002.####.jpg - 1-6',
            '/item2/v001/item2_v001.####.jpg - 101-105, 110-115',
            '/item2/v002/item2_v002.####.jpg - 101-105, 110-115',
            '/item2/v003/item2_v003.####.jpg - 101-105, 110-115',
            '/item3/v001/item3_v001.####.jpg - 101-105',
            '/item4/v001/item4_v001.####.jpg - 101',
            '/item4/v002/item4_v002.####.jpg - 101',
            '/item4/v003/item4_v003.####.jpg - 101',
        ]

        for i, r in enumerate(results):
            path = sequences.utils.join_paths(TEST_FILES_PATH, 'TestFlattening') + test_results[i]
            self.assertEqual(path, r)


if __name__ == '__main__':
    unittest.main(verbosity=2)
