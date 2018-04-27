import os

import perforce
import general

__all__ = [
    'FilestructurePath',
    'PerforcePath',
    'DiskPath',
]


class FilestructurePath(object):
    def __init__(self, path):
        self._path = general.path_normalize(path)
        self._type = None

    @classmethod
    def from_path(cls, path, *args, **kwargs):
        type = cls.find_type(path, *args, **kwargs)
        if type:
            instance = type(path, *args, **kwargs)
        else:
            instance = cls(path)
        return instance

    @classmethod
    def find_type(cls, path, *args, **kwargs):
        types = FilestructurePath.__subclasses__()
        types.sort(key=lambda x: x.priority, reverse=True)
        type = None
        for _type in types:
            try:
                _type(path, *args, **kwargs)
            except Exception:
                continue
            else:
                type = _type
                break
        return type

    @property
    def path(self):
        return self._path

    def parent(self):
        return os.path.dirname(self.path)

    def name(self):
        return os.path.basename(self.path)

    @property
    def type(self):
        return self._type


class PerforcePath(FilestructurePath):

    priority = 40

    _whereKeys = {
        'clientFile': True,
        'path': True,
        'depotFile': True,
    }

    _fileinfoKeys = {
        'rev': True,
        'time': True,
        'actio': True,
        'type': True,
        'depotFile': True,
        'change': True
    }

    _statsKeys = {
        'clientFile': True,
        'path': True,
        'depotFile': True,
        'headType': False,
        'headRev': False,
        'headChange': False,
        'headTime': False,
        'headModTime': False,
        'headAction': False,
        'isMapped': False,
        'haveRev': False,
        'otherOpen': False,
        'change': False,
    }

    def __init__(self, path, *args, **kwargs):
        super(PerforcePath, self).__init__(path)
        self._p4 = kwargs.pop('p4', None)
        self._clientData = kwargs.pop('clientData', None)
        self._where = kwargs.pop('where', None)
        self._client = None
        self._perforce_root = None

        self._data = {}
        self._loaded_cmds = set()

        self._input_path = path

        if path == '/':
            raise Exception("Can't create a Perforce instance from your system root path: {0}".format(path))

        if path[0:2] == "//":
            self._data['depotFile'] = general.path_normalize(path)
        else:
            self._data['path'] = general.path_normalize(path)

        if kwargs.get('validate', True):
            self.validate()

    @property
    def p4(self):
        return self._p4

    @p4.setter
    def p4(self, value):
        self._p4 = value

    @property
    def local_path(self):
        if 'path' in self._data:
            return self._data['path']
        return self.where.get('path')

    @property
    def depot_path(self):
        if 'depotFile' in self._data:
            return self._data['depotFile']
        return self.where.get('depotFile')

    def tracked(self):
        self.refresh()
        if self.stats and 'headRev' in self.stats:
            return True
        return False

    def get_stats(self):
        """
        Get Perforces stats (fstat) for this Perforce path
        This always retrieves the latest information, no caching
        """
        result = {}
        if self.p4.client:
            with perforce.TempP4ExceptionLevel(self.p4, 1):
                stats = self.p4.run_fstat("-Op", self._input_path)
                if stats:
                    result = stats[0]
        return result

    @property
    def stats(self):
        """
        Get Perforces stats (fstat) for this Perforce path
        Uses caching
        """
        result = {}
        cached = True
        for k in self._statsKeys:
            if k not in self._data:
                if self._statsKeys[k]:
                    cached = False
                    break
            else:
                result[k] = self._data[k]

        if cached or 'stats' in self._loaded_cmds:
            return result

        stats = self.get_stats()
        self._data.update(stats)
        self._loaded_cmds.add('stats')
        return stats

    @stats.setter
    def stats(self, value):
        if value is None:
            # Clear cache
            for k in self._statsKeys:
                if k in self._data:
                    del self._data[k]
            if 'stats' in self._loaded_cmds:
                self._loaded_cmds.remove('stats')
            return

        if not isinstance(value, dict):
            raise TypeError("Expected dict or None for stats, got {0}".format(value))

        self._data.update(value)

    def get_revisions(self):
        """
        Get Perforces revsions (filelog) for this Perforce path
        This always retrieves the latest information, no caching
        """
        if self.clientData and self.tracked:
            try:
                result = self.p4.run_filelog('-L', self.path)
            except perforce.P4.P4Exception:
                pass
            else:
                return sorted(result[0].each_revision(), key=lambda r: r.rev)
        return []

    @property
    def revisions(self):
        """
        Get Perforces revisions (filelog) for this Perforce path
        Uses caching
        """
        result = {}
        result = self._data.get('revisions', None)
        if result is not None:
            return result

        revisions = self.get_revisions()
        self._data['revisions'] = revisions
        self._loaded_cmds.add('revisions')
        return self._data['revisions']

    @revisions.setter
    def revisions(self, value):
        if value is None:
            # Clear cache
            if 'revisions' in self._data:
                del self._data['revisions']
            if 'revisions' in self._loaded_cmds:
                self._loaded_cmds.remove('revisions')
            return

        self._data['revisions'] = value
        self._loaded_cmds.add('revisions')

    def get_client_data(self):
        try:
            return perforce.get_client_data(self._p4)
        except ValueError:
            pass
        except Exception:
            pass
        return {}

    @property
    def clientData(self):
        if not self._clientData:
            self._clientData = self.get_client_data()
        return self._clientData

    def get_where(self):
        """
        Get Perforces where (where) for this Perforce path
        No caching
        """
        with perforce.TempP4ExceptionLevel(self.p4, 0):
            # "a" allows for matching roots
            where = self.p4.run_where(general.join_paths(self._input_path, '_A_'))

        if not where:
            return {}

        where = where[0]
        for k, v in where.items():
            if v.endswith('_A_'):
                where[k] = os.path.dirname(v)
        return where

    @property
    def where(self):
        """
        Get Perforces where (where) for this Perforce path
        Uses caching
        """
        result = {}
        cached = True
        for k in self._whereKeys:
            if k not in self._data:
                if self._whereKeys[k]:
                    cached = False
                    break
            else:
                result[k] = self._data[k]

        if cached or 'where' in self._loaded_cmds:
            return result

        where = self.get_where()
        self._data.update(where)
        self._loaded_cmds.add('where')
        return where

    @where.setter
    def where(self, value):
        if value is None:
            for k in self._whereKeys:
                if k in self._data:
                    del self._data[k]
            if 'where' in self._loaded_cmds:
                self._loaded_cmds.remove('where')
            return

        if not isinstance(value, dict):
            raise TypeError("Expected dict or None for where, got {0}".format(value))

        self._data.update(value)

    def get_fileinfo(self):
        """
        Get Perforces fileinfo (file) for this Perforce path
        No caching
        """
        with perforce.TempP4ExceptionLevel(self.p4, 1):
            result = self.p4.run_files(self._input_path)
        if not result:
            return {}
        return result[0]

    @property
    def fileinfo(self):
        """
        Get Perforces fileinfo (file) for this Perforce path
        Uses caching
        """
        result = {}
        cached = True
        for k in self._fileinfoKeys:
            if k not in self._data:
                if self._fileinfoKeys[k]:
                    cached = False
                    break
            else:
                result[k] = self._data[k]
        if cached or 'fileinfo' in self._loaded_cmds:
            return result

        fileinfo = self.get_fileinfo()
        self._data.update(fileinfo)
        self._loaded_cmds.add('fileinfo')
        return fileinfo

    @fileinfo.setter
    def fileinfo(self, value):
        if value is None:
            for k in self._fileinfoKeys:
                if k in self._data:
                    del self._data[k]
            if 'fileinfo' in self._loaded_cmds:
                self._loaded_cmds.remove('fileinfo')
            return

        if not isinstance(value, dict):
            raise TypeError("Expected dict or None for fileinfo, got {0}".format(value))

        self._data.update(value)

    def item_cmp(self, a, b):
        """
        Return the comparison for two items.
        Sort by isfile/isdir and then by name
        """
        t = -cmp(a.isdir, b.isdir)
        if t == 0:
            return cmp(a.name, b.name)
        else:
            return t

    def editable(self):
        if os.path.exists(self.local_path):
            return os.access(self.local_path, os.W_OK)
        else:
            dirpath = os.path.dirname(self.local_path)
            if os.path.exists(dirpath):
                return os.access(dirpath, os.W_OK | os.X_OK)
        return False

    def deleted(self):
        self.refresh()
        if self.stats and self.stats.get('headAction', None) == 'delete':
            return True
        return False

    def latest(self):
        if self.clientData and self.tracked and not self.deleted:
            if self.revision == max([r.rev for r in self.revisions]):
                return True
            else:
                return False
        return True

    def checkedOut(self):
        if self.clientData:
            result = self.p4.run_opened(self.path)
            if result:
                return True
        return False

    @property
    def different(self):
        if self.revision == 0:
            raise ValueError("Can't check if unsynced files have changed")
        try:
            changes = self.p4.run_diff('-f', self.local_path + '#{0}'.format(self.revision))
        except:
            return True
        if not changes:
            return False
        if len(changes) > 1:
            return True
        return False

    @property
    def revision(self):
        return int(self.stats.get('haveRev', 0))

    @property
    def next_revision(self):
        return max([r.rev for r in self.revisions] if self.revisions else [0]) + 1

    def exists(self):
        return perforce.is_path_tracked(self.path, p4=self.p4)

    def refresh(self):
        if self.isfile():
            self._loaded_cmds.clear()
            # Clear cache
            self.stats = None
            self.revisions = None
        else:
            if self._children is not None:
                for c in self._children:
                    c.refresh()

    def sync(self, revision=None, *args, **kwargs):
        rev = ''
        result = None
        if revision is not None:
            try:
                rev = '#{0}'.format(int(str(revision).lstrip('#')))
            except ValueError:
                raise ValueError('invalid revision number: {0}'.format(revision))
        try:
            if self.isfile():
                query = '{0}{1}'.format(self.path, rev)
            else:
                query = '{0}/...{1}'.format(self.path, rev)
            result = self.p4.run_sync(*(list(args) + [query]), **kwargs)
            self.refresh()
        except perforce.P4.P4Exception, e:
            if "file(s) up-to-date" in str(e):
                pass
            else:
                raise
        else:
            self.refresh()
        return result

    def remove(self):
        self.sync(revision=0)

    def checkout(self):
        if self.isfile:

            result = self.p4.run_edit(self.path)
        else:
            path = self.path
            if not path.endswith('/'):
                path += '/'
            path += '...'
            result = self.p4.run_edit(path)
        return result

    def revert(self):
        if self.isfile:
            result = self.p4.run_revert(self.path)
        else:
            path = self.path
            if not path.endswith('/'):
                path += '/'
            path += '...'
            result = self.p4.run_revert(path)
        return result

    def revert_unchanged(self):
        """Reverts unchanged file"""

        try:
            different = self.different
        except ValueError:
            return True

        if different:
            return False
        self.revert()
        return True

    def submit(self, description=None, force=False):
        result = []
        if description is None:
            if self.description is not None:
                description = self.description
            else:
                if self.tracked:
                    description = 'Updated file {0}'.format(self.perforce_path)
                else:
                    description = 'Added file {0}'.format(self.perforce_path)

        self.stats = None
        if self.stats.get('change', None):
            changeID = self.stats['change']
        if changeID != 'default' and not force:
            raise ValueError("File is already in changelist: {0}".format(changeID))

        # Create changelist
        change = perforce.build_changelist(self.p4, [self.path], description)

        # Save changelist
        change = self.p4.save_change(change)

        # Get changelist id
        changeID = change[0].split()[1]

        # Submit via id
        args = ['-c', changeID]

        result = self.p4.run_submit(*args)
        num = result[-1]['submittedChange']
        self.refresh()
        return self.p4.fetch_change(num)

    def get_children(self, includeDirs=True, includeFiles=True):
        if not self.isdir():
            return None

        def wrap_instances(cls, paths):
            instances = []
            for path in paths:
                instances.append(cls.__class__(path))
            return instances

        p4items = []
        kwargs = dict(
            p4=self.p4,
            path=self.path,
        )
        if includeDirs:
            paths = perforce.get_child_dirs(**kwargs)
            p4items.extend(wrap_instances(self, paths))
        if includeFiles:
            paths = perforce.get_child_files(**kwargs)
            p4items.extend(wrap_instances(self, paths))

        # supplement with disk children
        diskItems = []
        if self.exists():
            kwargs = dict(
                includeFiles=includeFiles,
                includeDirs=includeDirs,
            )
            diskItems = general.get_folder_contents(self.local_path, **kwargs)
            p4itemNames = [i.name for i in p4items]
            new = [i for i in diskItems if os.path.basename(i) not in p4itemNames]
            diskItems = wrap_instances(self, new)

        # combine and sort
        result = p4items + diskItems
        result.sort(cmp=self.item_cmp)

        # assign indices to children
        for i, r in enumerate(result):
            r.parent = self
            r.index = i

        return result

    def read(self, forceP4=False):
        if not self.isfile():
            return None

        if not forceP4:
            self.sync()
        if forceP4 or not self.exists():
            result = self.p4.run_print('-q', self.path)
            if isinstance(result, list):
                r = result[1]
                if isinstance(r, bytearray):
                    return r.decode('utf-8')
                else:
                    return r
            else:
                return result
        elif self.exists():
            try:
                with open(self.local_path, 'rb') as fp:
                    contents = fp.read()
            except IOError:
                pass
            else:
                return contents
        return None

    def isfile(self):
        if not self.exists():
            return False
        with perforce.TempP4ExceptionLevel(self.p4, 0):
            result = self.p4.run_fstat(self.path)
            if result:
                return True
        return False

    def isdir(self):
        if not self.exists():
            return False
        with perforce.TempP4ExceptionLevel(self.p4, 0):
            result = self.p4.run_fstat(self.path)
            if result:
                return False
        return True

    def validate(self):
        if self.p4 is None:
            self.p4 = perforce.get_p4_from_path(self.path)
        client = perforce.get_client_from_path(self.p4, self.path)
        self.p4.client = client
        if not client:
            raise ValueError("Couldn't find client for path: {0}".format(self.path))


class DiskPath(FilestructurePath):

    priority = 20

    def __init__(self, path):
        super(DiskPath, self).__init__(path)
        self.validate()

    @property
    def local_path(self):
        return self.path

    def exists(self):
        return os.path.exists(self.path)

    def editable(self):
        return os.access(self.path, os.W_OK | os.X_OK)

    def read(self):
        with open(self.path, 'r') as fp:
            data = fp.read()
        return data

    def get_children(self):
        if self.isfile():
            return None

        def wrap_instances(cls, paths):
            instances = []
            for path in paths:
                instances.append(cls.__class__(path))
            return instances

        files = general.get_folder_contents(self.path)
        result = wrap_instances(self, files)
        return result

    def isfile(self):
        return os.path.isfile(self.path)

    def isdir(self):
        return os.path.isdir(self.path)

    def validate(self):
        if not os.path.exists(self.path):
            raise ValueError("Path does not exist on disk")
