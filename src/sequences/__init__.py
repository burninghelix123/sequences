# -*- coding: utf-8 -*-

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

import utils                # NOQA
from core import *          # NOQA
