import os
from operator import itemgetter

import general

P4 = None
try:
    import P4
except:
    # some tools not functional without p4python
    pass

__all__ = [
    'refresh',
    'newInstance',
    'is_valid_user',
    'TempP4ExceptionLevel',
    'get_p4_and_client_from_path',
    'get_p4_from_path',
    'get_client_data',
    'get_client_from_path',
    'check_path_in_client',
    'find_client',
    'get_depots',
    'get_depot_paths',
    'get_clients',
    'get_clients_with_specs',
    'get_child_dirs',
    'get_child_files',
    'build_changelist',
    'is_path_tracked',
    'is_file_tracked',
    'is_dir_tracked',
]


DEFAULT_USER_VALIDATED = False
DEFAULT_LOGGED_IN = False

# Cache p4 instances and clients
P4_INSTANCES = {}
P4_DEPOTS = []
P4_CLIENTS = {}
P4_CLIENT_SPECS = {}


def refresh():
    """
    Delete all cached p4 connections
    """
    global P4_INSTANCE
    global P4_INSTANCES
    global P4_DEPOTS
    global P4_CLIENTS
    P4_INSTANCE = None
    P4_INSTANCES = {}
    P4_DEPOTS = []
    P4_CLIENTS = {}


def newInstance(dialog=False):
    global DEFAULT_USER_VALIDATED
    global DEFAULT_LOGGED_IN

    if P4 is None or not hasattr(P4, 'P4'):
        raise ValueError("Couldn't find P4 or P4API")

    p4 = P4.P4()
    if not p4.connected():
        p4.connect()

    if not DEFAULT_LOGGED_IN:
        if dialog:
            import gui
            gui.login(p4)
        else:
            try:
                p4.run_login("-s")
            except P4.P4Exception:
                raise ValueError("Couldn't login to P4")
        DEFAULT_LOGGED_IN = True

    if not DEFAULT_USER_VALIDATED:
        if not is_valid_user(p4):
            raise ValueError("P4 User Doesn't Exist: {0}".format(p4.user))
        DEFAULT_USER_VALIDATED = True

    return p4


def is_valid_user(p4):
    users = [x['User'] for x in p4.run_users()]
    if p4.user in users:
        return True
    return False


class TempP4ExceptionLevel(object):
    """
    Temporarily adjust the P4 exception level

    Example:
        >>> with TempP4ExceptionLevel(p4, 1):
        >>>     # do stuff

    Args:
        p4 (`P4.P4`): P4 instance
        lvl (`int`): Exception Level
    """
    def __init__(self, p4, lvl):
        self.p4 = p4
        self.lvl = lvl
        self.origLvl = None

    def __enter__(self):
        self.origLvl = self.p4.exception_level
        self.p4.exception_level = self.lvl

    def __exit__(self, type, value, tb):
        self.p4.exception_level = self.origLvl


def get_p4_and_client_from_path(path):
    """
    Given a path, return a p4 instance and clientData if possible.
    Will search within the cached instances, otherwise attempts
    to find an appropriate client and returns the new data
    """
    global P4_INSTANCES
    # check root and stream paths of cached client
    # data to see if this path is in one of them
    for c, data in P4_INSTANCES.items():
        root = data[1].get('Root')
        depot = data[1].get('Stream')
        if (root and general.path_contains(root, path))\
                or (depot and general.path_contains(depot, path)):
            return data

    p4 = newInstance()

    # If not logged in, no client can be found
    try:
        p4.run_login("-s")
    except P4.P4Exception:
        return p4, None

    # Find associated clients
    clientData = find_client(p4, path)

    # If none are found, we're done
    if not clientData:
        data = (p4, None)
        return p4, None

    # check to see if we already have an instance
    # with the same client data
    client = clientData.get('client')
    for c, data in P4_INSTANCES.items():
        if c == client:
            return data

    # Build a new instance and store it
    p4 = P4.P4()
    p4.client = client
    if not p4.connected():
        p4.connect()
    data = (p4, clientData)
    P4_INSTANCES[client] = data
    return data


def get_p4_from_path(path):
    p4 = P4.P4()
    if not p4.connected():
        p4.connect()
    try:
        p4.run_login("-s")
    except P4.P4Exception, e:
        raise ValueError("Couldn't login to perforce: {0}".format(e))
    client = get_client_from_path(p4, path)
    if not client:
        raise ValueError("Couldn't find client for path: {0}".format(path))
    p4.client = client
    if p4.client not in P4_INSTANCES:
        P4_INSTANCES[p4.client] = p4
    return p4


def get_client_data(p4):
    if not p4.run_clients('-e', p4.client):
        raise ValueError("Client Does Not Exist: {0}".format(p4.client))
    result = p4.fetch_client(p4.client)
    return result


def get_client_from_path(p4, path, clients=None, includeData=False):
    if clients is None:
        clients = p4.run_clients('-u', p4.user)
        clients.sort(key=lambda c: c['Access'], reverse=True)

    if not clients:
        return

    path = general.path_normalize(path).lower()

    # First check for matching clients with matching host
    _clients = filter(lambda c: c['Host'] == p4.host, clients)
    for _client in _clients:
        if check_path_in_client(p4, _client, path):
            if includeData:
                return _client
            return _client['client']

    # Search the rest of the clients that don't have a host set
    _clients = filter(lambda c: c['Host'] == "", clients)
    for _client in _clients:
        if check_path_in_client(p4, _client, path):
            if includeData:
                return _client
            return _client['client']

    # No Matches
    return


def check_path_in_client(p4, c, path, filterHost=True):
    def contains(a, b):
        return general.path_contains(a.lower(), b, normalize=False, normcase=False)

    # Perforce Depot Path, only need to check root
    if path[0:2] == "//":
        if 'Stream' in c:
            if contains(c['Stream'], path):
                # LOG.debug("Client matched by Stream: {0[client]} {0[Stream]}".format(c), extra=dict(indent=1))
                return True

        # Match based on the roots of the mappings
        # Ex:
        #   //depot/path/... //client/...
        #   ^^^^^^^^^^^^^^^^

        # Lazy load the view data since it requires an additional p4 call
        view = c.get('View', None)
        if view is None:
            _client = p4.fetch_client(c['client'])
            c.update(_client)
            view = c.get('View', None)

        for mapping in c.get('View', []):
            root = mapping.split(' ')[0]
            if root.startswith('-'):
                continue
            if root.endswith('...'):
                root = root[:-3]
            if contains(root, path):
                # LOG.debug("Client matched by view mapping root: {0} {1}".format(root, path))
                return True
        return False
    else:
        if contains(c['Root'], path):
            # LOG.debug("Client matched by Root: {0[client]} {0[Root]}".format(c), extra=dict(indent=1))
            return True
        for alt in c.get('AltRoots', []):
            if contains(alt, path):
                # LOG.debug("Client matched by AltRoot: {0[client]} {1}".format(c, alt), extra=dict(indent=1))
                return True

    return False


def find_client(p4, path, host=None):
    """
    Find a client by root path
    """
    if not p4.connected():
        raise ValueError("Perforce is not connected")
    # determine filter values
    if host is None:
        host = p4.host.lower()

    # find matches
    def clientContainsPath(c, path):
        _host = c.get('Host', None)
        if _host and _host.lower() != host:
            return False
        if general.path_contains(c['Root'], path):
            return True
        if 'Stream' in c:
            if general.path_contains(c['Stream'], path):
                return True
        for alt in c.get('AltRoots', []):
            if general.path_contains(alt, path):
                return True

        # Match based on the roots of the mappings
        # Ex:
        #   //depot/path/... //client/...
        #   ^^^^^^^^^^^^^^^^
        for mapping in c.get('View', []):
            root = mapping.split(' ')[0]
            if root.startswith('-'):
                continue
            if root.endswith('...'):
                root = root[:-3]
            if general.path_contains(root, path):
                return True
        return False

    clients = get_clients(p4)
    matches = [c for c in clients if clientContainsPath(c, path)]

    if not len(matches):
        # Check based on the client spec
        clients = get_clients_with_specs(p4, clients=clients, ignoreStreams=True)
        matches = [c for c in clients if clientContainsPath(c, path)]

    # check for explicitly set hostnames
    if len(matches) > 1:
        import socket
        hostname = socket.gethostname()
        _matches = filter(lambda m: m['Host'] == hostname, matches)
        if len(_matches):
            matches = _matches

    # check results
    if len(matches) > 1:
        matches.sort(key=itemgetter('Access'))
    elif not len(matches):
        return
    return matches[0]


def get_depots(p4=None, refresh=False):
    """
    Return a list of all depots
    """
    global P4_DEPOTS
    if not P4_DEPOTS or refresh:
        if p4 is None:
            p4 = newInstance()
        P4_DEPOTS = p4.run_depots()
    return P4_DEPOTS


def get_depot_paths(p4=None, refresh=False):
    """
    From a p4 instance, get a list of all depot paths available

    Args:
        p4 (P4): perforce instance

    Returns:
        list of str: Depot paths in the format of
            ['//{depotName}', ...]
    """
    depots = get_depots(p4, refresh)
    return ['//{0[name]}'.format(d) for d in depots]


def get_clients(p4=None, refresh=False):
    """
    Return a list of all clients
    """
    if p4 is None:
        p4 = newInstance()
    if p4.user not in P4_CLIENTS or refresh:
        P4_CLIENTS[p4.user] = p4.run_clients('-u', p4.user)
    return P4_CLIENTS[p4.user]


def get_clients_with_specs(p4=None, clients=None, ignoreStreams=False, useCache=True):
    """
    Get a list of clients with their full specs
    This contains the view mappings
    """
    if p4 is None:
        p4 = newInstance()

    result = []

    if clients is None:
        clients = get_clients(p4)

    clientsToMatch = []
    if useCache:
        for client in clients:
            clientName = client['client']
            if clientName in P4_CLIENT_SPECS:
                result.append(P4_CLIENT_SPECS[clientName])
            else:
                clientsToMatch.append(client)
    else:
        clientsToMatch = clients[:]

    for i, client in enumerate(clientsToMatch):
        clientName = client['client']
        if ignoreStreams and client.get('Stream', None):
            continue
        data = p4.run_client('-o', client['client'])[-1]
        newData = dict(client.items())
        newData.update(data)
        P4_CLIENT_SPECS[clientName] = newData
        result.append(newData)

    return result


def get_child_dirs(p4, path, **kwargs):
    """
    Return all child directories of the given path as strings
    Kwargs are passed to filter_item
    """
    searchPath = "{0}/*".format(path)
    result = []
    try:
        dirsResult = p4.run_dirs(searchPath)
    except P4.P4Exception:
        dirsResult = []
    for r in dirsResult:
        path = general.path_normalize(r['dir'])
        basename = os.path.basename(path)
        if general.filter_item(basename, **kwargs):
            result.append(path)
    return result


def get_child_files(p4, path, includeDeleted=False, **kwargs):
    """
    Return all perforce files inside the given directory as strings
    """
    searchPath = "{0}/*".format(path)
    result = []
    try:
        filesResult = p4.run_files(searchPath)
    except P4.P4Exception:
        filesResult = []
    for f in filesResult:
        deleted = f.get('action', '').endswith('delete')
        if not deleted or includeDeleted:
            path = general.path_normalize(f['depotFile'])
            basename = os.path.basename(path)
            if general.filter_item(basename, **kwargs):
                result.append(path)
    return result


def build_changelist(p4, files, description):
    change = p4.fetch_change()
    change._files = files
    change._description = description
    return change


def is_path_tracked(path, p4=None):
    if p4 is None:
        p4 = get_p4_from_path(path)
    return is_file_tracked(path, p4) or is_dir_tracked(path, p4)


def is_file_tracked(path, p4=None):
    """
    Return True if the given file is currently tracked in perforce
    """
    if p4 is None:
        p4 = get_p4_from_path(path)
    try:
        info = p4.run_files(path)
    except P4.P4Exception:
        return False
    else:
        if len(p4.errors):
            return False
    if len(info):
        if info[0]['action'] == 'delete':
            # File was deleted, and thus has to be readded
            return False
        return True
    return False


def is_dir_tracked(path, p4=None):
    """ Return True if the given directory is currently tracked in perforce """
    if p4 is None:
        p4 = get_p4_from_path(path)
    try:
        info = p4.run_dirs(path)
    except P4.P4Exception:
        return False
    else:
        if len(p4.errors):
            return False
    return bool(len(info))
