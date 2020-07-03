import os
import threading
from tinydb import TinyDB, Query, where
from typing import Optional
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware
try:
    from .constants import CONFIG
except ImportError:
    from constants import CONFIG

TinyDB.default_table_name = 'users'
CachingMiddleware.WRITE_CACHE_SIZE=1

class DB:
    Lock = threading.Lock()
    def __init__(self, path: Optional[str]=None):
        if path is None:
            path = os.path.join(CONFIG['DEFAULT_CONFIG_DIR'],'nauta_db.json')
        self._db = TinyDB(path, storage=CachingMiddleware(JSONStorage), indent=2)
        self._query = Query()

    def __contains__(self, key):
        return self._db.contains(self._query.username == key)

    def __iter__(self):
        for i in self._db:
            yield i

    def get(self, key: str, default=None):
        r = default
        with self.Lock:
            r = self._db.get(self._query.username == key)
        return r

    def get_by_alias(self, key: str, default=None):
        r = default
        with self.Lock:
            r = self._db.get(self._query.alias == key)
        return r

    def get_aliases(self):
        r=[]
        with self.Lock:
            r = self._db.search(self._query.alias!='' and self._query.alias!=None)
        return r


    def set(self, key: str, data: dict):
        with self.Lock:
            self._db.update(data, self._query.username == key)

    def set_by_alias(self, key: str, data: dict):
        with self.Lock:
            self._db.update(data, self._query.alias == key)

    def insert(self, key:str, data: dict):
        with self.Lock:
            self._db.insert(data)

    def remove(self, key:str):
        with self.Lock:
            self._db.remove(self._query.username == key)

    def remove_by_alias(self, key:str):
        with self.Lock:
            self._db.remove(self._query.alias == key)
