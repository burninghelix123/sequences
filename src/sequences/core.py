#!/usr/bin/env python

import os
import re
import logging
import collections
from itertools import count, groupby

import scandir
from utils import path_normalize, join_paths, fileStructure

P4 = None
try:
    import P4
except:
    pass
if not hasattr(P4, "P4") or not callable(P4.P4):
    P4 = None

__all__ = [
    'AbstractSequence',
    'FileSequence',
    'BaseSequence',
    'ImageSequence',
    'scan_for_files',
    'flatten_sequences',
    'get_sequence_range',
]

ROOTLOG = logging.getLogger()
LOG = logging.getLogger(__name__)

DEFAULT_SEQUENCE_PATTERN = re.compile(
    '^(?P<prefix>.*?)'
    '(?P<sequence>'
        '(?P<nums>(?:\d)+)'
        '|(?P<pounds>(?:#)+)'
        '|(?P<regex>\\\\d{\d+})'
        '|(?P<formatstring>{\w+:\d+d})'
        '|(?P<percent>%\d+d)'
    ')$'
)  # NOQA

DEFAULT_FILE_SEQUENCE_PATTERN = re.compile(
    '^(?P<prefix>.*?)'
    '(?:\.'
        '(?P<sequence>'
            '(?P<nums>(?:\d)+)'
            '|(?P<pounds>(?:#)+)'
            '|(?P<regex>\\\\d{\d+})'
            '|(?P<formatstring>{\w+:\d+d})'
            '|(?P<percent>%\d+d)'
        ')'
        '(?P<suffix>.*'
            '(?P<ext>\.\S+$)'
            '|$'
        ')'
    ')'
)  # NOQA

SEQUENCE_FORMAT_TYPES = [
    'nums',
    'pounds',
    'regex',
    'formatstring',
    'percent'
]

# Profiling
REGEX_COUNTER = 0
SYSCALL_COUNTER = 0

IMAGE_EXTENSIONS = [
    'tiff', 'tif', 'png', 'tga', 'jpg', 'jpeg',
    'raw', 'bmp', 'gif', 'dpx', 'exr', 'psd',
]


class AbstractSequence(collections.Mapping):
    regex = DEFAULT_SEQUENCE_PATTERN
    formatStringKey = 'item'
    sequenceFormatTypes = SEQUENCE_FORMAT_TYPES

    def __init__(self, string, items=None, skipValidate=False, allowNegative=False):
        """
        Initalize a base sequence

        Args:
            string (str): Sequence string
                Sequence must be prefixed by a period if it's not at
                    the begining of a string

                    00001
                    mySequence.0001
                              ^

                Only one sequence can exist in a string
                    Ex:
                        mySequence.0020.something.0001
                    Only this one will be used -> ^^^^

                Item number must be the last item in the string
                    Ex:
                    Yes
                        mySequence.0001
                                   ^^^^
                    No
                        0001.mySequence

                    No
                        mySequence.0001.something

                Sequence must be one of the below formats:
                    Ex:
                        mySequence.00001                (Numbers)
                        mySequence.#####                (Pound String)
                        mySequence.{FORMATKEY:05d}      (Format String) (Internal)
                        mySequence.%05d                 (Percent String)
                        mySequence.\d{5}                (Regex Pattern)

            items (list of str, optional): List of item strings to use as the sequence items
                These items must be in the numbers format
            skipValidate (bool, optional): Whether to skip validation on init
            allowNegative (bool, optional): Whether to allow negative item numbers

        """
        self._string = string
        self._input_items = items
        self._allow_negative = allowNegative  # TODO Not yet implemented

        self._clearProperties()

        if not skipValidate:
            self.validate()

    def __getitem__(self, index):
        # Added support for using slices
        if not isinstance(index, slice):
            return self.items[index]
        result = []
        start, end, step = self._parse_slice_indices(index)
        for x in range(start, end + 1, step):
            if x in self.items:
                result.append(self.items[x])
        return result

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return sorted(self.items).__iter__()

    def _clearProperties(self):
        self._matches = []
        self._primary_match = None
        self._format_type = None

        self._current_item = None
        self._current_item_number = None

        self._sequence_items = collections.OrderedDict()
        self._regex_string = None

        self._parsed = False
        self._built = False
        self._prefix = None
        self._suffix = None
        self._ext = None
        self._range = None

    def reload(self):
        self._clearProperties()
        self._loadSequenceItems()

    def setSource(self, string):
        self._string = string
        self.reload()

    def setItems(self, items):
        self._input_items = items
        self.reload()

    def _loadSequenceItems(self):
        """
        List of all items in the current sequence

        Args:
            value (list of str): List of sequence items

        Returns:
            dict: keys are #'s and values are the items
                Ex:
                    {
                        10: 'aaa010.0010',
                        11: 'aaa010.0012',
                    }
        """
        if not self.parsed:
            self._parse_values()
        if not self._built:
            if self._input_items is not None:
                items = self._build_sequence_items_from_input()
                self._sequence_items.update(sorted(items.items(), key=lambda i: i[0]))
                self._built = True
        return self._sequence_items

    @property
    def items(self):
        """
        List of items in the version

        Returns:
            list of str: paths
        """
        if not self._built:
            self._loadSequenceItems()
        result = self._sequence_items
        return result

    @property
    def parsed(self):
        return self._parsed

    @property
    def built(self):
        return self._built

    @property
    def firstItem(self):
        """
        First string item in the sequence

        Returns:
            str
        """
        if len(self.items):
            return self[self.items.keys()[0]]
        return None

    @property
    def firstItemNumber(self):
        """
        First string item number

        Returns:
            int
        """
        if len(self.items):
            return self.items.keys()[0]
        return None

    @property
    def midItem(self):
        """
        Mid string item in the sequence

        Returns:
            str
        """
        if len(self.items):
            return self[self.items.keys()[len(self.items.keys())/2]]
        return None

    @property
    def midItemNumber(self):
        """
        mid string item number

        Returns:
            int
        """
        if len(self.items):
            return self.items.keys()[len(self.items.keys())/2]
        return None

    @property
    def lastItem(self):
        """
        Last string item in the sequence

        Returns:
            str
        """
        if len(self.items):
            return self[self.items.keys()[-1]]
        return None

    @property
    def lastItemNumber(self):
        """
        last string item number

        Returns:
            int
        """
        if len(self.items):
            return self.items.keys()[-1]
        return None

    @property
    def string(self):
        """
        Input sequence string

        Returns:
            str
        """
        return self._string

    @property
    def formatType(self):
        """
        Format type of the input sequence
        Ex:
            aaa010.#####.png
            ->
            pounds

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        return self._format_type

    @property
    def currentItem(self):
        """
        Current item for the sequence value from
        the input sequence

        Ex:
            aaa010.00001.png
                   ^^^^^
            ->
            00001

            aaa010.#####.png
                   ^^^^^
            ->
            #####

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        return self._current_item

    @property
    def currentItemNumber(self):
        """
        If the input sequence had a current item number
        return it

        Ex:
            aaa010.00001.png
                   ^^^^^
            ->
            1

        Args:
            value (int): New item number

        Returns:
            int or None
        """
        if not self.parsed:
            self._parse_values()
        return self._current_item_number

    @currentItemNumber.setter
    def currentItemNumber(self, value):
        if not isinstance(value, int):
            raise TypeError("Item number must be an integer")
        self._current_item_number = value
        self._current_item = '%0{0}d'.format(int(self.padding)) % self._current_item_number

    @property
    def padding(self):
        """
        Level of padding for the sequence

        Returns:
            int
        """
        if not self.parsed:
            self._parse_values()
        return self._padding

    @property
    def prefix(self):
        """
        Prefix of the file sequence

        Returns:
            str
        """
        if self._prefix is not None:
            return self._prefix
        if not self.parsed:
            self._parse_values()
        result = self._primary_match.groupdict().get('prefix', None)
        if result is None:
            result = ''
        self._prefix = result
        return result

    @property
    def suffix(self):
        """
        Prefix of the file sequence

        Returns:
            str
        """
        if self._suffix is not None:
            return self._suffix
        if not self.parsed:
            self._parse_values()
        result = self._primary_match.groupdict().get('suffix', None)
        if result is None:
            result = ''
        self._suffix = result
        return result

    @property
    def numbers(self):
        """
        List of all sequence item numbers

        Returns:
            list of int
        """

        if not self._built:
            self._loadSequenceItems()
        result = [self.num(s[1]) for s in self.items.items()]
        return result

        # return sorted(self.items.keys())

    @property
    def range(self):
        """
        Range of item numbers

        Returns:
            tuple of ints: (firstItemNumber, lastItemNumber)
        """
        if self._range is not None:
            return self._range
        if not self._parsed:
            self._parse_values()

        def as_range(g):
            l = list(g)
            if l[0] == l[-1]:
                return [l[0]]
            return [l[0], l[-1]]

        grouped_numbers = [as_range(x) for _, x in groupby(self.numbers, lambda x, c=count(): next(c)-x)]
        self._range = grouped_numbers
        return self._range

    @property
    def missing(self):
        from itertools import imap, chain
        from operator import sub
        results = list(chain.from_iterable((self.numbers[i] + d for d in xrange(1, diff))
            for i, diff in enumerate(imap(sub, self.numbers[1:], self.numbers))
            if diff > 1))
        return results

    def rename(self, padding=None, startFrame=None, ignoreMissing=False, replace=False, dryrun=False, progressCB=None):
        # Validate we have something to rename
        if padding is None and startFrame is None:
            return
        elif not self.items or not self.numbers:
            LOG.debug("Sequence has no items")
            return
        elif startFrame is None and int(padding) == int(self.padding):
            LOG.debug("Sequence padding already matches, nothing to rename")
            return
        elif padding is None and int(startFrame) == int(self.firstNumber):
            LOG.warning("Sequence startframe already matches, nothing to rename")
            return
        elif int(padding) == int(self.padding) and int(startFrame) == int(self.firstNumber):
            LOG.warning("Sequence already matches, nothing to rename")
            return
        if not ignoreMissing and len(self.range) > 1:
            raise ValueError("Cannot rename sequences with missing frames")

        # Set defaults if not defined
        if padding is None:
            padding = self.padding
        if startFrame is None:
            startFrame = self.numbers[0]

        # Get the offset/change from current startFrame and new startFrame
        frameOffset = 0
        if startFrame:
            frameOffset = startFrame - self.numbers[0]

        # Build list of paths of new rename paths
        renamePaths = []
        for item, num in zip(self.items, self.numbers):
            newNum = num + frameOffset
            newPath = self.prefix + ".%0{0}d".format(padding) % newNum + self.suffix
            renamePaths.append((item.path, newPath))

        # Reverse the order of renaming so we don't overwrite as we rename
        reverse = True
        if not startFrame or startFrame < self.numbers[0]:
            reverse = False
        if reverse:
            renamePaths = list(reversed(renamePaths))

        # Rename the files
        completedOps = {}
        errored = False
        for index, paths in enumerate(renamePaths):
            oldPath, newPath = paths
            if dryrun and newPath in completedOps.keys():
                # Since dryrun isn't actually renaming the files, check if the newPath was something previously renamed
                # That way we don't error for something that exists, that wouldn't exist had dryRun been turned off
                pass
            elif os.path.exists(newPath) and not replace:
                LOG.error("Error already exists while copying {0} -> {1}".format(oldPath, newPath))
                errored = True
                break
            if dryrun:
                LOG.info("Copying {0} -> {1}".format(os.path.basename(oldPath), os.path.basename(newPath)))
                completedOps[oldPath] = (oldPath, newPath)
                continue
            try:
                os.rename(oldPath, newPath)
            except Exception, e:
                LOG.exception(e)
                errored = True
                break
            else:
                completedOps[oldPath] = (oldPath, newPath)
                progressCB(index, len(renamePaths))

        # If it errored Undo what we managed to rename
        if errored:
            for oldPath, newPath in completedOps.values():
                if dryrun:
                    continue
                os.rename(newPath, oldPath)

        # Change source sequence path
        else:
            if self._format_type == 'nums':
                newNum = self.sourceNumber + frameOffset
                newPath = self.get_string(newNum, padding=padding)
            elif self._format_type == 'pounds':
                newPath = self.get_pound_string(padding=padding)
            elif self._format_type == 'regex':
                newPath = self.get_regex_string(padding=padding)
            elif self._format_type == 'formatstring':
                newPath = self.get_format_string(padding=padding)
            elif self._format_type == 'percent':
                newPath = self.get_percent_string(padding=padding)
            else:
                raise ValueError("Invalid Format Type Found")
            self.setSource(newPath)

    def get_string(self, itemNumber, padding=None):
        """
        Return the sequence with the sequence numbers replaced with #
        Ex:
            aaa010.00001.png
            -> itemNumber=5
            aaa010.00005.png

        Args:
            itemNumber (int): The item number to use
            padding (int, optional): Custom padding level to use
                If not supplied, uses the padding from the input sequence

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        template = self.get_format_string(padding=padding)
        result = template.format(**{self.formatStringKey: itemNumber})
        return result

    def get_pound_string(self, padding=None):
        """
        Return the sequence with the sequence numbers replaced with #
        Ex:
            aaa010.00001.png
            ->
            aaa010.#####.png

        Args:
            padding (int, optional): Custom padding level to use
                If not supplied, uses the padding from the input sequence

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        if padding is None:
            padding = self.padding
        substr = '#'*int(padding)
        result = substr.join(self._base_sequence_items)
        return result

    def get_format_string(self, padding=None, formatKey=None):
        """
        Returns the sequence with the sequence numbers replaced with a format string
        Ex:
            aaa010.00001.png
            ->
            aaa010.{item:05d}.png

        Args:
            padding (int, optional): Custom padding level to use
                If not supplied, uses the padding from the input sequence
            formatKey (str, optional): Custom format key to use
                If not supplied, uses the default format key for the class

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        if formatKey is None:
            formatKey = self.formatStringKey
        if padding is None:
            padding = self.padding
        substr = '{{{0}:0{1}d}}'.format(formatKey, int(padding))
        result = substr.join(self._base_sequence_items)
        return result

    def get_percent_string(self, padding=None):
        """
        Return the sequence with the sequence numbers replaced with
        old python style string formatting
        Ex:
            aaa010.00001.png
            ->
            aaa010.%05d.png

        Args:
            padding (int, optional): Custom padding level to use
                If not supplied, uses the padding from the input sequence

        Returns:
            str
        """
        if not self.parsed:
            self._parse_values()
        if padding is None:
            padding = self.padding
        substr = '%0{0}d'.format(int(padding))
        result = substr.join(self._base_sequence_items)
        return result

    def get_regex_string(self, padding=None):
        """
        Return the sequence with the sequence numbers replaced with a regex pattern
        Ex:
            aaa010.00001.png
            ->
            aaa010.\d{5}.png

        Args:
            padding (int, optional): Custom padding level to use
                If not supplied, uses the padding from the input sequence

        Returns:
            str
        """
        if self._regex_string:
            return self._regex_string
        if not self.parsed:
            self._parse_values()
        if padding is None:
            padding = self.padding
        substr = '\d{{{0}}}'.format(int(padding))
        result = substr.join(self._base_sequence_items)
        self._regex_string = result.replace('[', '\\[')
        return self._regex_string

    def num(self, string):
        """
        Return the number component of a sequenced string.

        Args:
            string (str): Sequence item

        >> num('apples.012')
        '012'
        """
        if not self.parsed:
            self._parse_values()
        if not self.is_part_of_sequence(string):
            raise ValueError("Item is not part of the sequence")

        start = self._primary_match.start('sequence')
        end = start + self.padding
        num = string[start:end]
        if num.isdigit():
            num = int(num)
            return num

    def is_part_of_sequence(self, string):
        """
        Check if the supplied string is part of this version

        Args:
            string (str): Can be any string format

        Returns:
            bool
        """
        # This checks for differences in padding

        if len(self.string) != len(string):
            return False

        # dirname = os.path.dirname(string)
        # old_dirname = self.folder

        # if dirname != old_dirname:
        #     return False

        if not self._parsed:
            self._parse_values()

        if not string.startswith(self.prefix):
            return False

        if not string.endswith(self.suffix):
            return False

        # TODO: Is regex matching still needed? Is something left after suffix and prefix? Looking for use cases.
        # try:
        #     pat = "^" + self.get_regex_string() + "$"
        # except:
        #     pat = "^" + self.string + "$"

        # match = re.match(pat, string)
        # if not match:
        #     return False

        return True

    def get_next_item(self, itemNumber=None):
        """
        Get the next item in the sequence.

        Args:
            itemNumber(int, optional): Item number to use as the starting point.
                If not supplied, will use the sequences current item number.
                If the sequence does not have a current item number, it will raise an error.

        Returns:
            str or None: item string for next item, or None if already the last item
        """
        if not self.parsed:
            self._parse_values()
        if itemNumber is None:
            itemNumber = self.currentItemNumber
            if itemNumber is None:
                raise ValueError("No item number supplied, and no current item number set")
        else:
            itemNumber = int(itemNumber)
        nums = self.numbers
        if itemNumber not in nums:
            raise ValueError("Invalid item number, missing item: {0}".format(itemNumber))
        itemIndex = nums.index(itemNumber)
        if itemIndex == (len(nums) - 1):
            # Already last item in the sequence
            return None
        return self.get_string(self.items.items()[itemIndex][0] + 1)
        # return self.items.items()[itemIndex][0] + 1

    def get_previous_item(self, itemNumber=None):
        """
        Get the previous item in the sequence.

        Args:
            itemNumber(int, optional): Item number to use as the starting point.
                If not supplied, will use the sequences current item number.
                If the sequence does not have a current item number, it will raise an error.

        Returns:
            str or None: item string for next item, or None if already the first item
        """
        if not self.parsed:
            self._parse_values()
        if itemNumber is None:
            itemNumber = self.currentItemNumber
            if itemNumber is None:
                raise ValueError("No item number supplied, and no current item number set")
        else:
            itemNumber = int(itemNumber)
        nums = self.numbers
        if itemNumber not in nums:
            raise ValueError("Invalid item number, missing item: {0}".format(itemNumber))
        itemIndex = nums.index(itemNumber)
        if itemIndex == 0:
            # Already first item in the sequence
            return None
        return self.get_string(self.items.items()[itemIndex][0] - 1)
        # return self.items[itemIndex - 1]

    def refresh(self):
        """
        Refresh the list of sequence items
        Not implemented in base class
        """
        pass

    def validate(self):
        """
        Parse and validate that the input sequence
        is actually a sequence

        Raises:
            ValueError: if not a sequence
        """
        if self.parsed:
            return True
        self._parse_values()

    @classmethod
    def validate_path(cls, path):
        global REGEX_COUNTER    # Profiling

        if not isinstance(path, basestring):
            raise TypeError("Input sequence must be a string, got {0}".format(type(path)))

        match = cls.regex.search(path)
        REGEX_COUNTER += 1      # Profiling

        if not match:
            raise ValueError("Invalid sequence, sequence pattern did not match: {0}".format(path))

        groups = match.groupdict()

        format_type = None
        for key in groups:
            if key in cls.sequenceFormatTypes and groups[key]:
                if key == 'formatstring':
                    formatKey = groups[key][1:].split(':')[0]
                    if formatKey != cls.formatStringKey:
                        raise ValueError("Wrong format key for sequence: {0}".format(groups[key]))
                format_type = key
        if format_type is None:
            raise ValueError("Invalid sequence, no valid format type matched")

        return match, groups, format_type

    def _parse_values(self, match=None, groups=None, formatType=None):
        """
        Process the input string through the sequence regex
        and parse all the base sequence information out of it
        """
        # Clear cached properties
        self._ext = None
        self._prefix = None
        self._suffix = None
        self._range = None

        if not match:
            match, groups, formatType = self.validate_path(self.string)
        self._matches.append(match)
        self._primary_match = match
        self._format_type = formatType

        self._current_item = groups['sequence']
        if self._format_type == 'nums':
            self._current_item_number = int(self._current_item)

        self._padding = self._parse_padding_from_match(match, self._format_type)

        # Used to build all other formats
        self._base_sequence_items = [self.string[:match.start('sequence')], self.string[match.end('sequence'):]]

        self._parsed = True

    def _parse_padding_from_match(self, match, formatType):
        """
        Based on the type of string supplied, get the level of padding the sequence contains
        """
        matchGrps = match.groupdict()

        if formatType == 'nums':
            return len(matchGrps['nums'])

        elif formatType == 'pounds':
            return len(matchGrps['pounds'])

        elif formatType == 'regex':
            match = matchGrps['regex'].lstrip('\d+{{').rstrip('}}')
            return int(match)

        elif formatType == 'formatstring':
            match = matchGrps['formatstring'].lstrip('{{{0}:'.format(self.formatStringKey)).rstrip('d}}')
            return int(match)

        elif formatType == 'percent':
            match = matchGrps['percent'].lstrip('%').rstrip('d')
            return int(match)

        else:
            raise TypeError("Unknown format type: {0}".format(formatType))

    def _build_sequence_items_from_input(self):
        """
        Build the internal dictionary of sequence items
        This is stored in key value format with the
        item number as the key and the sequence string as the value.

        Returns:
            dict: sequence items
                Ex:
                    {
                        '10': 'aaa010.0010.png',
                    }
        """
        result = {}
        for item in self._input_items:
            num = self.num(item)
            result[num] = item

        # Add the initial item
        if self.currentItemNumber:
            result[self.currentItemNumber] = self._string
        return result

    def _parse_slice_indices(self, slice):
        """
        Used for handling slices in get item
        """
        start = slice.start
        end = slice.stop
        step = slice.step
        if not isinstance(step, int):
            step = 1
        if not isinstance(start, int):
            start = self.firstItemNumber
        if not isinstance(end, int):
            end = self.lastItemNumber
        return start, end, step


class BaseSequence(AbstractSequence, collections.MutableMapping):
    """
    Base Sequence

    Mutable sequence based only on supplied strings.

    Args:
        string (str): Sequence string
            Sequence must be prefixed by a period if it's not at
                the begining of a string

                00001
                mySequence.0001
                          ^

            Only one sequence can exist in a string
                Ex:
                    mySequence.0020.something.0001
                Only this one will be used -> ^^^^

            Item number must be the last item in the string
                Ex:
                Yes
                    mySequence.0001
                               ^^^^
                No
                    0001.mySequence

                No
                    mySequence.0001.something

            Sequence must be one of the below formats:
                Ex:
                    mySequence.00001                (Numbers)
                    mySequence.#####                (Pound String)
                    mySequence.{FORMATKEY:05d}      (Format String) (Internal)
                    mySequence.%05d                 (Percent String)
                    mySequence.\d{5}                (Regex Pattern)

        items (list of str): List of item strings
            These items must be in the numbers format
        skipValidate (bool): Whether to skip validation on init
        allowNegative (bool): Whether to allow negative item numbers

    """

    def __delitem__(self, index):
        if isinstance(index, slice):
            start, end, step = self._parse_slice_indices(index)
            for x in range(start, end+1, step):
                if x in self.items.keys():
                    del self.items[x]
        else:
            if index in self.items.keys():
                del self.items[index]

    def __setitem__(self, index, value):
        if not self.is_part_of_sequence(value):
            raise ValueError("Item is not part of this sequence: {0}".format(value))
        if self.num(value) != index:
            raise ValueError("Can't assign sequence to index of different value than the item number")

        updated = False

        for key in self.items.keys():
            if index == key:
                self.items[key] = value
                updated = True
                break

        items = self.items.items()
        if not updated:
            items.append((index, value))

        self._sequence_items = collections.OrderedDict(sorted(items, key=lambda i: i[0]))


class FileSequence(AbstractSequence):
    regex = DEFAULT_FILE_SEQUENCE_PATTERN

    def __init__(self, path, items=None, skipValidate=False, allowNegative=False, validateExists=True, fileInstance=None, normalizeInput=True):
        """
        File Sequence

        Mutable sequence based on actual scanned files unless a list of items is provided for caching.
        Does not currently inherit base class because we don't want the deleting of items from a sequence consisting of files.

        Args:
            path (str): Sequence string
                Sequence must be prefixed by a period if it's not at
                    the begining of the path

                    path/to/00001.png
                    path/to/mySequence.0001.png
                                      ^

                Only one sequence can exist in a string. If multiple exist,
                    only the last sequence is used.

                    Ex:
                        mySequence.0020.something.0001
                    Only this one will be used -> ^^^^

                File number must be between periods
                    Ex:
                        mySequence.0001.png
                    This works -> ^----^
                        0001.mySequence.png
                    Not ^^^^
                        mySequence.png.0001
                    And Not this ->    ^^^^

                Sequence must be one of the below formats:
                    Ex:
                        mySequence.00001                (Numbers)
                        mySequence.#####                (Pound String)
                        mySequence.{FORMATKEY:05d}      (Format String) (Internal)
                        mySequence.%05d                 (Percent String)
                        mySequence.\d{5}                (Regex Pattern)

            items (list of str): List of paths in the sequence
                These items must be in the numbers format
            skipValidate (bool): Whether to skip validation on init
            allowNegative (bool): Whether to allow negative item numbers

        """
        if normalizeInput:
            path = path_normalize(path)
        self._sourcePath = path
        self._sourceFile = fileInstance
        self.validateExists = validateExists
        # path = path_normalize(os.path.abspath(path))
        super(FileSequence, self).__init__(self._sourcePath, items=items, skipValidate=skipValidate, allowNegative=allowNegative)

    def reload(self):
        self._clearProperties()

    def setSource(self, path, fileInstance=None):
        self._sourcePath = path_normalize(path)
        self._sourceFile = fileInstance
        self._string = self._sourcePath
        self.reload()

    def setSourceFromFilestructure(self, fileInstance):
        self._sourceFile = fileInstance
        self._sourcePath = path_normalize(fileInstance.path)
        self._string = self._sourcePath
        self.reload()

    def setItems(self, paths):
        instances = []
        for path in paths:
            fileInstance = fileStructure.FilestructurePath.from_path(path)
            instances.append(fileInstance)
        self._input_items = instances
        self.reload()

    def setItemsFromFilestructure(self, items):
        self._input_items = items
        self.reload()

    @classmethod
    def validate_path(cls, path, validateExists=True):
        global REGEX_COUNTER    # Profiling

        if not isinstance(path, basestring):
            raise TypeError("Input sequence must be a string, got {0}".format(type(path)))

        match = cls.regex.search(path)
        REGEX_COUNTER += 1      # Profiling

        if not match:
            raise ValueError("Invalid sequence, sequence pattern did not match: {0}".format(path))

        groups = match.groupdict()

        format_type = None
        for key in groups:
            if key in cls.sequenceFormatTypes and groups[key]:
                if key == 'formatstring':
                    formatKey = groups[key][1:].split(':')[0]
                    if formatKey != cls.formatStringKey:
                        raise ValueError("Wrong format key for sequence: {0}".format(groups[key]))
                format_type = key
        if format_type is None:
            raise ValueError("Invalid sequence, no valid format type matched")

        if validateExists:
            if not os.path.exists(os.path.dirname(path)):
                raise ValueError("Folder for sequence doesn't exist: {0}".format(os.path.dirname(path)))

        return match, groups, format_type

    @classmethod
    def from_fileInstance(cls, instance, items=None, skipValidate=False, validateExists=True, allowNegative=False, p4=None, clientData=None):
        result = cls(instance.path, items=items, skipValidate=skipValidate, allowNegative=allowNegative, validateExists=validateExists, fileInstance=instance)
        return result

    @classmethod
    def from_item_paths(cls, paths, skipValidate=False, validateExists=True, allowNegative=False, p4=None, clientData=None):
        match = None
        groups = None
        formatType = None
        paths = [path_normalize(x) for x in paths]
        if not skipValidate:
            match, groups, formatType = cls.validate_path(paths[0], validateExists=validateExists)
        result = cls(paths[0], items=paths, skipValidate=True, allowNegative=allowNegative, validateExists=validateExists)
        result._parse_values(match, groups, formatType)
        return result

    @classmethod
    def from_item_files(cls, files, skipValidate=False, validateExists=True, allowNegative=False):
        match = None
        groups = None
        formatType = None
        if not skipValidate:
            match, groups, formatType = cls.validate_path(files[0].path, validateExists=validateExists)
        result = cls(path_normalize(files[0].path), items=[path_normalize(x.path) for x in files], skipValidate=True, allowNegative=allowNegative, validateExists=validateExists)
        result._parse_values(match, groups, formatType)
        return result

    @property
    def sourceFile(self):
        if self._sourceFile is None:
            self._sourceFile = fileStructure.FilestructurePath.from_path(self._sourcePath)
        return self._sourceFile

    @property
    def sourceClass(self):
        return self.sourceFile.__class__

    @property
    def sourcePath(self):
        if self._sourcePath is None:
            self._sourcePath = self.sourceFile.path
        return self._sourcePath

    @property
    def sourceLocalPath(self):
        return self.sourceFile.local_path

    @property
    def sourceNumber(self):
        number = self.num(self.sourcePath)
        return number

    # Last
    @property
    def lastFile(self):
        if not self.files:
            return self.sourceFile
        return self.files[-1]

    @property
    def lastPath(self):
        return self.lastFile.path

    @property
    def lastLocalPath(self):
        return self.lastFile.local_path

    @property
    def lastNumber(self):
        number = self.num(self.lastPath)
        return number

    # First
    @property
    def firstFile(self):
        if not self.files:
            return self.sourceFile
        return self.files[0]

    @property
    def firstPath(self):
        if not self.paths:
            return self.sourcePath
        return self.paths[0]

    @property
    def firstLocalPath(self):
        return self.firstFile.local_path

    @property
    def firstNumber(self):
        number = self.num(self.firstPath)
        return number

    # Middle
    @property
    def middleFile(self):
        if not self.files:
            return self.sourceFile
        return self.files[len(self.files) / 2]

    @property
    def middlePath(self):
        if not self.paths:
            return self.sourcePath
        return self.paths[len(self.paths) / 2]

    @property
    def middleLocalPath(self):
        return self.middleFile.local_path

    @property
    def middleNumber(self):
        number = self.num(self.middlePath)
        return number

    @property
    def files(self):
        """
        List of files in the sequence

        Returns:
            list of str: paths
        """
        if not self._built:
            self._loadSequenceItems()
        result = [fileStructure.FilestructurePath.from_path(s[1]) for s in self._sequence_items.items()]
        return result

    @property
    def paths(self):
        """
        List of files in the sequence

        Returns:
            list of str: paths
        """
        if not self._built:
            self._loadSequenceItems()
        result = [s[1] for s in self._sequence_items.items()]
        return result

    @property
    def localPaths(self):
        """
        List of files in the sequence

        Returns:
            list of str: paths
        """
        if not self._built:
            self._loadSequenceItems()
        result = [fileStructure.FilestructurePath.from_path(s[1]).local_path for s in self._sequence_items.items()]
        return result

    @property
    def numbers(self):
        """
        List of files in the sequence

        Returns:
            list of str: paths
        """
        if not self._built:
            self._loadSequenceItems()
        result = [self.num(s[1]) for s in self._sequence_items.items()]
        return result

    def get_file(self, number, padding=None):
        """
        Returns the version file instance with the provided number
        """
        if not self._parsed:
            self._parse_values()
        template = self.get_format_string(padding=padding)
        result = template.format(**{self.formatStringKey: number})

        if issubclass(self.sourceClass, fileStructure.PerforcePath):
            parentWhere = {}
            for k, v in self.sourceFile.where.items():
                parentWhere[k] = os.path.dirname(v)
            fileInstance = self.sourceClass(result, p4=self.sourceFile.p4, clientData=self.sourceFile.clientData, where=parentWhere)
        else:
            fileInstance = self.sourceClass(result)
        return fileInstance

    def get_path(self, number, padding=None):
        """
        Returns the version path with the provided number
        """
        if not self._parsed:
            self._parse_values()
        template = self.get_format_string(padding=padding)
        result = template.format(**{self.formatStringKey: number})
        return result

    def isInPerforce(self, file):
        if not P4:
            return False
        if isinstance(file, fileStructure.PerforcePath):
            # Checking is tracked prevents finding files for sequences when the source path isn't tracked
            # I.e. if frame 1 is provided but only 101-105 exist, 101-105 should still be found or vice versa
            return True
        else:
            return False

    def _parse_values(self, match=None, groups=None, formatType=None):
        """
        Process the input string through the sequence regex
        and parse all the base sequence information out of it
        """
        global REGEX_COUNTER    # Profiling

        # Clear cached properties
        self._ext = None
        self._prefix = None
        self._suffix = None
        self._range = None

        if not match:
            match, groups, formatType = self.validate_path(self.string, validateExists=self.validateExists)
        self._matches.append(match)
        self._primary_match = match
        self._format_type = formatType

        self._current_item = groups['sequence']
        if self._format_type == 'nums':
            self._current_item_number = int(self._current_item)

        self._padding = self._parse_padding_from_match(match, self._format_type)

        # Used to build all other formats
        self._base_sequence_items = [self.string[:match.start('sequence')], self.string[match.end('sequence'):]]

        self._parsed = True

    def _loadSequenceItems(self):
        """
        List of all items in the current sequence

        Args:
            value (list of str): List of sequence items

        Returns:
            dict: keys are #'s and values are the items
                Ex:
                    {
                        10: 'path/to/aaa010.0010.png',
                        11: 'path/to/aaa010.0012.png',
                    }
        """
        if not self._parsed:
            self._parse_values()
        if not self._built:
            if self._input_items is not None:
                items = self._build_sequence_items_from_input()
                self._built = True
            elif self.isInPerforce(self.sourcePath):
                items = self._build_sequence_items_from_perforce()
                self._built = True
            else:
                items = self._build_sequence_items_from_disk()
                self._built = True
            self._sequence_items.update(sorted(items.items(), key=lambda i: i[0]))
        return self._sequence_items

    @property
    def ext(self):
        """
        Extension of the file sequence

        Returns:
            str
        """
        if self._ext is not None:
            return self._ext
        if not self._parsed:
            self._parse_values()
        result = self._primary_match.groupdict()['ext']
        if result is None:
            result = ''
        self._ext = result
        return result

    @property
    def folder(self):
        """
        Path to the folder containing the sequence

        Returns:
            str
        """
        return os.path.dirname(self.sourcePath)

    @property
    def localFolder(self):
        """
        Path to the folder containing the sequence

        Returns:
            str
        """
        return os.path.dirname(self.sourceLocalPath)

    def _build_sequence_items_from_input(self):
        """
        Build the internal dictionary of sequence items
        This is stored in key value format with the
        item number as the key and the sequence string as the value.

        Returns:
            dict: sequence items
                Ex:
                    {
                        '10': 'aaa010.0010.png',
                    }
        """
        result = {}
        for path in self._input_items:
            if self.is_part_of_sequence(path):
                num = self.num(path)
                result[num] = path

        # Add the initial item
        if self.is_part_of_sequence(self.sourcePath):
            result[self.sourceNumber] = self.sourcePath
        return result

    def _build_sequence_items_from_disk(self):
        """
        Build disk items from scanning the items in the sequence folder

        Returns:
            dict: sequence items
                Ex:
                    {
                        '10': 'path/to/aaa010.0010.png',
                    }
        """
        global REGEX_COUNTER    # Profiling
        global SYSCALL_COUNTER  # Profiling

        result = {}
        folderPath = self.folder

        SYSCALL_COUNTER += 1    # Profiling

        SYSCALL_COUNTER += 1    # Profiling
        start = self._primary_match.start('sequence')
        end = start + self.padding
        for dirEntry in scandir.scandir(folderPath):
            dirEntryPath = join_paths(folderPath, dirEntry.name)
            if not dirEntry.is_file():
                continue

            if not self.is_part_of_sequence(dirEntryPath):
                continue

            # If we've got this far, we know that this sequence item matches
            # the format of our input sequence exactly.
            # So we can use the match start and end of our primary match
            # to extract the number from this path
            if end > len(dirEntryPath):
                continue
            num = dirEntryPath[start:end]
            if not num.isdigit():
                # Not a digit in the same spot so not part of sequence
                continue
            if dirEntryPath[start:end+1].isdigit():
                # Extra numbers found, has different padding, not part of sequence
                continue
            num = int(num)

            path = self.get_path(num)
            result[num] = path
        return result

    def _build_sequence_items_from_perforce(self):
        """
        Build disk items from scanning the items in the sequence folder

        Returns:
            dict: sequence items
                Ex:
                    {
                        '10': 'path/to/aaa010.0010.png',
                    }
        """
        global REGEX_COUNTER    # Profiling
        global SYSCALL_COUNTER  # Profiling

        result = {}
        folderPath = self.folder

        parentWhere = {}
        for k, v in self.sourceFile.where.items():
            parentWhere[k] = os.path.dirname(v)

        p4Dir = fileStructure.PerforcePath(folderPath, p4=self.sourceFile.p4, clientData=self.sourceFile.clientData, where=parentWhere, validate=False)

        SYSCALL_COUNTER += 1    # Profiling

        SYSCALL_COUNTER += 1    # Profiling
        start = self._primary_match.start('sequence')
        end = start + self.padding
        for dirEntry in p4Dir.children:
            dirEntryPath = dirEntry.path

            if not isinstance(dirEntry, fileStructure.PerforcePath):
                continue

            if not dirEntry.isfile():
                continue

            if not self.is_part_of_sequence(dirEntryPath):
                continue

            # If we've got this far, we know that this sequence item matches
            # the format of our input sequence exactly.
            # So we can use the match start and end of our primary match
            # to extract the number from this path
            if end > len(dirEntryPath):
                continue
            num = dirEntryPath[start:end]
            num = int(num)

            path = self.get_path(num)
            result[num] = path
        return result


class ImageSequence(FileSequence):
    """
    Image Sequence

    Same as file sequence with extra file extension validation for images.
    """
    imageExtensions = IMAGE_EXTENSIONS
    formatStringKey = 'frame'

    @classmethod
    def validate_path(cls, path, validateExists=True):
        """
        Parse and validate that the input sequence
        is actually an image sequence

        Raises:
            ValueError: if not a sequence
        """
        match, groups, format_type = super(ImageSequence, cls).validate_path(path, validateExists=validateExists)
        ext = os.path.splitext(path)[-1]
        ext = ext.lstrip('.')
        if ext not in cls.imageExtensions:
            raise ValueError("Path extension is not a valid image extension: {0}".format(ext))
        return match, groups, format_type


def scan_for_files(path, recursive=False, groupFolders=False, _result=None):
    """
    Scans for files under a folder, optionally recursive and optionally grouping based on each directory.
    """
    if _result is None:
        _result = []
    result = []
    try:
        for entry in scandir.scandir(path):
            entryPath = join_paths(path, entry.name)
            if entry.is_dir():
                if not recursive:
                    continue
                scan_for_files(entryPath, groupFolders=groupFolders, recursive=recursive, _result=_result)
            else:
                result.append(entryPath)

    # Handle paths that are too long
    except OSError:
        path = os.path.abspath(path)
        if not path.startswith('\\\\?\\') and path.startswith("\\\\"):
            path = "\\\\?\\UNC\\" + path[2:]
        try:

            for entry in scandir.scandir(path):
                entryPath = join_paths(path, entry.name)
                if entry.is_dir():
                    if not recursive:
                        continue
                    scan_for_files(entryPath, groupFolders=groupFolders, recursive=recursive, _result=_result)
                else:
                    result.append(entryPath)
        except Exception, e:
            LOG.warning("Couldn't scan path: {0} - {1}".format(path, e))

    if result:
        if groupFolders:
            _result.append(result)
        else:
            _result.extend(result)
    return _result


def flatten_sequences(paths, validateExists=False, normalizeInput=False):
    """
    Flatten Sequences from a list of paths
    """
    results = {}
    while paths:
        path = paths.pop()
        # Check if path is a sequence
        try:
            seq = FileSequence(path, validateExists=validateExists, normalizeInput=normalizeInput)
        except Exception:
            results[path] = None
            continue

        new_path = seq.get_pound_string()
        if new_path not in results:
            results[new_path] = seq

        # Filter out other paths of sequence
        for path in paths:
            if seq.is_part_of_sequence(path):
                paths.remove(path)

    return results


def get_sequence_range(path, validateExists=False):
    """
    Get the frame range for a sequence in an easy to ready format
    """
    try:
        seqObj = FileSequence(path, validateExists=validateExists)
        seqRange = seqObj.range
    except:
        sequenceNums = None
    else:
        if not seqRange:
            sequenceNums = None
            return sequenceNums
        sequenceNums = ""
        for index, nums in enumerate(seqRange):
            if len(nums) > 1:
                sequenceNums += "{0}-{1}".format(*nums)
            else:
                sequenceNums += "{0}".format(nums[0])
            if not index == len(seqRange) - 1:
                sequenceNums += ", "
        return sequenceNums
