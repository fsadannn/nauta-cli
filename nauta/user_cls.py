import json
from typing import Optional, Union

class User:
    __slots__ = ('_username', '_password', '_time_left',
                 '_expire_date', '_alias', '_last_update', '_credit')
    def __init__(self, username: str, password: str, credit: Optional[str]=None,
                time_left: Optional[str]=None, expire_date: Optional[str]=None,
                alias: Optional[str]=None, last_update: Optional[Union[str, int]]=0):
        self._username = username
        self._password = password
        self._time_left = time_left
        self._expire_date = expire_date
        self._alias = alias
        self._last_update = last_update
        self._credit = credit

    def to_json(self):
        return {'username': self._username, 'password': self._password,
                'time_left': self._time_left, 'expire_date': self._expire_date,
                'last_update': self._last_update, 'alias': self._alias,
                "credit": self._credit}

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)

    def __str__(self):
        return json.dumps(self.to_json())

    @property
    def username(self):
        return self._username

    @property
    def last_update(self):
        return self._last_update

    @last_update.setter
    def last_update(self, update: Union[str,int]):
        self._last_update = update

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, update: str):
        self._password = update

    @property
    def time_left(self):
        return self._time_left

    @time_left.setter
    def time_left(self, update: str):
        self._time_left = update

    @property
    def credit(self):
        return self._credit

    @credit.setter
    def credit(self, update: str):
        self._credit = update

    @property
    def expire_date(self):
        return self._expire_date

    @expire_date.setter
    def expire_date(self, update: str):
        self._expire_date = update

    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, update: str):
        self._alias = update

    def update_time_left(self, ntime: str, callback=None):
        self._time_left = ntime
        if callback:
            callback(self)

    def update_last_update(self, ntime: Union[str, int], callback=None):
        self._last_update = ntime
        if callback:
            callback(self)

    def update_expire_date(self, ndate: str, callback=None):
        self._expire_date = ndate
        if callback:
            callback(self)

    def update_alias(self, nalias: str, callback=None):
        self._alias = nalias
        if callback:
            callback(self)

    def update_password(self, password: str, callback=None):
        self._password = password
        if callback:
            callback(self)
