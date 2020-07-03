import os
import time
import logging
import logging.handlers
from typing import Dict, List, Union, Any, Optional
from requests import Session
import requests
from parsel import Selector

from .constants import NautaState, LogLevel, CONFIG
from .user_cls import User
from .utils import get_inputs, get_info, human_secs
from .utils import verify as verifyy
from .db import DB
from .exceptions import UserExist, ConectionError
from .exceptions import BadCredentials, BadAlias

logger = logging.getLogger('Nauta')
logger.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler('nauta.log', maxBytes=1024*1024, backupCount=2)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


class Nauta:

    __slots__=('_lang', '_state', '_db', '_ss')

    def __init__(self, lang='esp', cache_path: Optional[str]=None,
                session:Optional[Session]=None):

        if session is not None:
            ss = session
        else:
            ss = Session()
            ss.headers['User-Agent']=CONFIG['USER_AGENT']
        self._ss = ss
        self._db = DB(None if cache_path is None else cache_path)

        self._state = NautaState.OFFLINE
        self._lang=lang

    def card_add(self, username: str, password: str, verify=True, raise_exception=False):
        info = None
        if username in self._db:
            logger.error(f'function \"card_add\"\nmsg: The user "{username}" already exist.')
            if raise_exception:
                raise UserExist(f'The user "{username}" already exist.')
            print(f'The user "{username}" already exist.')
            return False
        if verify:
            try:
                vv = verifyy(username, password, self._ss)
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
                logger.error(f'function \"card_add\"\nmsg: Looks like there is no connection now. Credentials can\'t be verify.\n{str(e)}')
                if raise_exception:
                    raise ConectionError("Looks like there is no connection now. Credentials can't be verify.")
                print("Looks like there is no connection now. Credentials can't be verify.")
                return False
            if not vv:
                logger.error(f'function \"card_add\"\nmsg: Credentials seem incorrect.')
                if raise_exception:
                    raise BadCredentials("Credentials seem incorrect.")
                print("Credentials seem incorrect.")
                return False
            try:
                info = get_info(username, password, self._ss)
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                pass
        user = User(username,password)
        if info:
            user.time_left = info['time_left']
            user.credit = info['credit']
            user.expire_date = info['expiration']
        self._db.insert(username, user.to_json())
        return True

    def card_delete(self, card: str):
        if card in self._db:
            self._db.remove(card)
        elif self._db.get_by_alias(card) is not None:
            self._db.remove_by_alias(card)

    def card_add_alias(self, username: str, alias: str, raise_exception=False):
        if username not in self._db:
            logger.error(f'function \"card_add_alias\"\nmsg: Credentials seem incorrect.')
            if raise_exception:
                raise BadCredentials("Credentials seem incorrect.")
            print("Credentials seem incorrect.")
            return False
        u_al = self._db.get_by_alias(alias)
        if u_al is not None and u_al['username']!=username:
            logger.error(f'function \"card_add_alias\"\nmsg: Alias \"{alias}\" already exist for other user.')
            if raise_exception:
                raise BadAlias(f"Alias \"{alias}\" already exist for other user.")
            return False
        self._db.set(username,{'alias': alias})
        return True

    def card_update(self, card: str, data: dict, raise_exception=False):
        if card in self._db:
            self._db.set(card, data)
            return True
        elif self._db.get_by_alias(card) is not None:
            self._db.set_by_alias(card, data)
            return True
        logger.error(f'function \"card_update_password\"\nmsg: Credentials seem incorrect.')
        if raise_exception:
            raise BadCredentials("Credentials seem incorrect.")
        return False

    def card_update_password(self, card: str, password: str, raise_exception=False):
        if card in self._db:
            self._db.set(card, {'password': password})
            return True
        elif self._db.get_by_alias(card) is not None:
            self._db.set_by_alias(card, {'password': password})
            return True
        logger.error(f'function \"card_update_password\"\nmsg: Credentials seem incorrect.')
        if raise_exception:
            raise BadCredentials("Credentials seem incorrect.")
        return False

    def verify(self, username: str, password: str):
        return verifyy(username, password, self._ss)


    def get_card(self, user: str, as_dict=False, try_update=True):
        if user in self._db:
            cd = self._db.get(user)
        else:
            cd = self._db.get_by_alias(user)
            if cd is None:
                return None
        user=User.from_json(cd)
        if try_update:
            try:
                info = get_info(user.username, user.password, self._ss)
                user.time_left = info['time_left']
                user.credit = info['credit']
                user.expire_date = info['expiration']
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
                logger.warning(f'function \"get_card\"\n{str(e)}')
        if as_dict:
            return cd
        return user

    def get_cards(self, as_dict=False):
        for i in self._db:
            if as_dict:
                yield i
            else:
                yield User.from_json(i)

    def get_alias(self, as_dict=False):
        for i in self._db.get_aliases():
            if as_dict:
                yield i
            else:
                yield User.from_json(i)

    def up_cli(self, usern: str):
        session = self._ss
        try:
            r = session.get("http://google.com")
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
            logger.info(f'function \"up_cli\"\nmsg: Looks like there is no connection now.\n{str(e)}')
            print("Looks like there is no connection now.")
            return

        sel = Selector(text=r.text)
        action = sel.css('form')[-1].xpath('@action').get()
        if ('google.com' in ''.join(r.cookies.list_domains()) and
            not 'secure.etecsa.net' in action):
            logger.info(f'function \"up_cli\"\nmsg: Looks like you\'re already connected. Use \'nauta down\' to log out.')
            print("Looks like you're already connected. Use 'nauta down' to log out.")
            return

        user = self._db.get(usern)
        if user is None:
            user = self._db.get_by_alias(usern)
            if user is None:
                logger.error(f'function \"up_cli\"\nmsg: Invalid card: {usern}.')
                print(f"Invalid card: {usern}.")
                return
        user = User.from_json(user)
        password = user.password
        username = user.username

        info = get_info(user.username, user.password, self._ss)
        user.time_left = info['time_left']
        user.credit = info['credit']
        user.expire_date = info['expiration']

        print(f"Using card {username}. Time left: {user.time_left}. Credit: {user.credit}")
        logger.debug(f"Using card {username}. Time left: {user.time_left}. Credit: {user.credit}")

        form = get_inputs(sel)
        form['username'] = username
        form['password'] = password

        csrfhw = form['CSRFHW']
        wlanuserip = form['wlanuserip']
        last_attribute_uuid = ""
        try:
            last_attribute_uuid = open(CONFIG['ATTR_UUID_FILE'], "r").read().strip()
        except FileNotFoundError:
            pass

        guessed_logout_url = (
            "https://secure.etecsa.net:8443/LogoutServlet?" +
            "CSRFHW={}&" +
            "username={}&" +
            "ATTRIBUTE_UUID={}&" +
            "wlanuserip={}"
        ).format(
            csrfhw,
            username,
            last_attribute_uuid,
            wlanuserip
        )
        with open(CONFIG['LOGOUT_URL_FILE'], "w") as f:
            f.write(guessed_logout_url + "\n")

        logger.debug("Attempting connection. Guessed logout url: "+guessed_logout_url)
        try:
            r = session.post(action, form)
            m = re.search(r'ATTRIBUTE_UUID=(\w+)&CSRFHW=', r.text)
            attribute_uuid = None
            if m:
                attribute_uuid = m.group(1)
        except:
            attribute_uuid = None

        if attribute_uuid is None:
            print("Log in failed :(")
            logger.error("Log in failed :(")
        else:
            with open(CONFIG['ATTR_UUID_FILE'], "w") as f:
                f.write(attribute_uuid + "\n")
            login_time = int(time.time())
            logout_url = (
                "https://secure.etecsa.net:8443/LogoutServlet?" +
                "CSRFHW={}&" +
                "username={}&" +
                "ATTRIBUTE_UUID={}&" +
                "wlanuserip={}"
            ).format(
                csrfhw,
                username,
                attribute_uuid,
                wlanuserip
            )
            with open(CONFIG['LOGOUT_URL_FILE'], "w") as f:
                f.write(logout_url + "\n")
            print("Logged in successfully. To logout, run 'nauta down'")
            print("or just hit Ctrl+C here, I'll stick around...")
            logger.debug("Connected. Actual logout URL is: '{}'".format(logout_url))
            if logout_url == guessed_logout_url:
                logger.debug("Guessed it right ;)")
            else:
                logger.debug("Bad guess :(")
            try:
                self._state = NautaState.CONNECTED
                while True:
                    print("\rConnection time: {} ".format(
                        human_secs(int(time.time()) - login_time)
                    ), end="")
                    time.sleep(1)
                    if not os.path.exists(CONFIG['LOGOUT_URL_FILE']):
                        break
            except KeyboardInterrupt:
                print("Got a Ctrl+C, logging out...")
                logger.info("Got Ctrl+C. Attempting disconnect...")
                r = session.get(logout_url)
                print(r.text)
                self._state = NautaState.OFFLINE

                now = int(time.time())
                logger.debug("Response to logout request: '{}'".format(r.text))
                logger.info("Connection time: "+human_secs(now - login_time))

                info = get_info(user.username, user.password, self._ss)
                user.time_left = info['time_left']
                user.credit = info['credit']
                user.expire_date = info['expiration']
                self._db.set(user.username, user.to_json())
                print("Reported time left:", info['time_left'])
                print("Reported credit:", info['credit'])
                logger.info("Reported time left: "+info['time_left'])
                logger.info("Reported credit: "+ info['credit'])

    def down(self):
        try:
            logout_url = open(CONFIG['LOGOUT_URL_FILE']).read().strip()
        except FileNotFoundError:
            print("Connection seems to be down already. To connect, use 'nauta up'")
            return
        session = self._ss
        print("Logging out...")
        r = session.get(logout_url)
        print(r.text)
        if 'SUCCESS' in r.text:
            self._state = NautaState.OFFLINE
            os.remove(CONFIG['LOGOUT_URL_FILE'])

    def up_gui(self, usern, callback=None):
        if not callback:
            def nothing(txt, opt=None):
                pass
            callback=nothing
        session = self._ss
        try:
            r = session.get("http://google.com")
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
            logger.info(f'function \"up_cli\"\nmsg: Looks like there is no connection now.\n{str(e)}')
            if self._lang=='esp':
                callback("Parece que no hay connexion en este momento.", LogLevel.WARNING)
            else:
                callback("Looks like there is no connection now.", LogLevel.WARNING)
            return 1

        sel = Selector(text=r.text)
        action = sel.css('form')[-1].xpath('@action').get()
        if ('google.com' in ''.join(r.cookies.list_domains()) and
            not 'secure.etecsa.net' in action):
            logger.info(f'function \"up_cli\"\nmsg: Looks like you\'re already connected. Use \'nauta down\' to log out.')
            if self._lang=='esp':
                callback("Parece que ya está connectado.", LogLevel.WARNING)
            else:
                callback("Looks like you're already connected.", LogLevel.WARNING)
            return 1

        user = self._db.get(usern)
        if user is None:
            user = self._db.get_by_alias(usern)
            if user is None:
                logger.error(f'function \"up_cli\"\nmsg: Invalid card: {usern}.')
                print(f"Invalid card: {usern}.")
                return
        user = User.from_json(user)
        password = user.password
        username = user.username

        info = get_info(user.username, user.password, self._ss)
        user.time_left = info['time_left']
        user.credit = info['credit']
        user.expire_date = info['expiration']

        if self._lang=='esp':
            callback(f"Utilizando cuenta {username}. Tiempo restante: {user.time_left}. Crédito: {user.credit}.", LogLevel.INFORMATION)
        else:
            callback(f"Using card {username}. Time left: {user.time_left}. Credit: {user.credit}.", LogLevel.INFORMATION)
        logger.debug(f"Using card {username}. Time left: {user.time_left}. Credit: {user.credit}")

        form = get_inputs(sel)
        form['username'] = username
        form['password'] = password

        csrfhw = form['CSRFHW']
        wlanuserip = form['wlanuserip']
        last_attribute_uuid = ""
        try:
            last_attribute_uuid = open(CONFIG['ATTR_UUID_FILE'], "r").read().strip()
        except FileNotFoundError:
            pass

        guessed_logout_url = (
            "https://secure.etecsa.net:8443/LogoutServlet?" +
            "CSRFHW={}&" +
            "username={}&" +
            "ATTRIBUTE_UUID={}&" +
            "wlanuserip={}"
        ).format(
            csrfhw,
            username,
            last_attribute_uuid,
            wlanuserip
        )
        with open(CONFIG['LOGOUT_URL_FILE'], "w") as f:
            f.write(guessed_logout_url + "\n")

        logger.debug("Attempting connection. Guessed logout url: "+guessed_logout_url)
        #pprint("Calling session.post:")
        #pprint({"action": action,
        #        "form": form})
        try:
            r = session.post(action, form)
            m = re.search(r'ATTRIBUTE_UUID=(\w+)&CSRFHW=', r.text)
            attribute_uuid = None
            if m:
                attribute_uuid = m.group(1)
        except:
            attribute_uuid = None

        if attribute_uuid is None:
            logger.error("Log in failed :(")
            if self._lang=='esp':
                callback("Fallo en el logueo :(", LogLevel.ERROR)
            else:
                callback("Log in failed :(", LogLevel.ERROR)
            return 1
        else:
            with open(CONFIG['ATTR_UUID_FILE'], "w") as f:
                f.write(attribute_uuid + "\n")
            logout_url = (
                "https://secure.etecsa.net:8443/LogoutServlet?" +
                "CSRFHW={}&" +
                "username={}&" +
                "ATTRIBUTE_UUID={}&" +
                "wlanuserip={}"
            ).format(
                csrfhw,
                username,
                attribute_uuid,
                wlanuserip
            )
            with open(CONFIG['LOGOUT_URL_FILE'], "w") as f:
                f.write(logout_url + "\n")
            if self._lang=='esp':
                callback("Logueado exitosamente.",LogLevel.INFORMATION)
            else:
                callback("Logged in successfully.",LogLevel.INFORMATION)
            logger.debug("Connected. Actual logout URL is: '{}'".format(logout_url))
            if logout_url == guessed_logout_url:
                logger.debug("Guessed it right ;)")
            else:
                logger.debug("Bad guess :(")
            self._state = NautaState.CONNECTED
        return 0

    def down_gui(self, callback=None):
        if not callback:
            def nothing(txt, opt=None):
                pass
            callback=nothing
        try:
            logout_url = open(CONFIG['LOGOUT_URL_FILE']).read().strip()
        except FileNotFoundError:
            callback("Connection seems to be down already.",LogLevel. WARNING)
            return 1
        session = self._ss
        callback("Logging out...", LogLevel.INFORMATION)
        r = session.get(logout_url)
        callback(r.text, LogLevel.INFORMATION)
        if 'SUCCESS' in r.text:
            self._state = NautaState.OFFLINE
            os.remove(CONFIG['LOGOUT_URL_FILE'])
            return 0