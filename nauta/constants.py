import os
import json
from enum import Enum, unique
import logging

@unique
class NautaState(Enum):
    OFFLINE = 0
    CONNECTED = 1
    USER_ERROR = 2
    LOG_FAIL = 3

@unique
class LogLevel(Enum):
    INFORMATION = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    DEBUG = logging.DEBUG
    NAME = 8

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.local/share/nauta")

CONFIG = {
    "USER_AGENT": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.98 Safari/537.36',
    "DEFAULT_CONFIG_DIR": DEFAULT_CONFIG_DIR,
    "ATTR_UUID_FILE": os.path.join(DEFAULT_CONFIG_DIR, "attribute_uuid"),
    "LOGOUT_URL_FILE": os.path.join(DEFAULT_CONFIG_DIR, "logout_url"),
    "TIME_CONVERSION_CONSTANT": 0.8
}

if os.path.exists(os.path.join(DEFAULT_CONFIG_DIR,'config.json')):
    CONFIG = json.load(open(os.path.join(DEFAULT_CONFIG_DIR,'config.json')))
