from pprint import pprint
from textwrap import dedent

import subprocess
import requests
import shelve
import json
import time
import bs4
import sys
import os
import re

import logging

LOCKER = True
try:
    import lockfile
except ImportError:
    LOCKER = False

PARSER = 'lxml'
try:
    import lxml
except ImportError:
    PARSER = 'html.parser'

CONFIG_DIR = os.path.expanduser("~/.local/share/nauta")

os.makedirs(CONFIG_DIR,exist_ok=True)


CARDS_DB = os.path.join(CONFIG_DIR, "cards")
ATTR_UUID_FILE = os.path.join(CONFIG_DIR, "attribute_uuid")
LOGOUT_URL_FILE = os.path.join(CONFIG_DIR, "logout_url")
logfile = open(os.path.join(CONFIG_DIR, "connections.log"), "a")

OFFLINE = 0
CONNECTED = 1
USER_ERROR = 2
LOG_FAIL = 3

INFORMATION = 0
WARNING = 1
ERROR = 2
DEBUG = 3

def log(*args, **kwargs):
    date = subprocess.check_output("date").decode().strip()
    kwargs.update(dict(file=logfile))
    print(
        "{:.3f} ({})".format(
            time.time(),
            date,
        ),
        *args,
        **kwargs,
    )
    logfile.flush()

def human_secs(secs):
    return "{:02.0f}:{:02.0f}:{:02.0f}".format(
        secs // 3600,
        (secs % 3600) // 60,
        secs % 60,
    )

class User:
    __slots__ = ('__username', '__password', '__time_left',
                 '__expire_date', '__alias', '__last_update')
    def __init__(self, username: str, password: str):
        self.__username = username
        self.__password = password
        self.__time_left = None
        self.__expire_date = None
        self.__alias = None
        self.__last_update = 0

    @property
    def username(self):
        return self.__username

    @property
    def last_update(self):
        return self.__last_update

    @property
    def password(self):
        return self.__password

    @property
    def time_left(self):
        return self.__time_left

    @property
    def expire_date(self):
        return self.__expire_date

    @property
    def alias(self):
        return self.__alias

    def update_time_left(self, ntime, callback=None):
        self.__time_left = ntime
        if callback:
            callback(self)

    def update_last_update(self, ntime, callback=None):
        self.__last_update = ntime
        if callback:
            callback(self)

    def update_expire_date(self, ndate, callback=None):
        self.__expire_date = ndate
        if callback:
            callback(self)

    def update_alias(self, nalias, callback=None):
        self.__alias = nalias
        if callback:
            callback(self)

    def update_password(self, password, callback=None):
        self.__password = password
        if callback:
            callback(self)

    def json(self):
        return {'username': self.__username, 'password': self.__password,
                'time_left': self.__time_left, 'expire_date': self.__expire_date,
                'last_update': self.__last_update, 'alias': self.__alias}

    def __str__(self):
        return json.dumps(self.json())


class DataBase:
    __slots__ = ('__data', '__lock')
    def __init__(self):
        self.__data = shelve.open(CARDS_DB)
        self.__lock = None
        if LOCKER:
            self.__lock = lockfile.LockFile(CARDS_DB+'.lock')

    def keys(self):
        return self.__data.keys()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__data.close()
        if LOCKER:
            if self.__lock.i_am_locking():
                try:
                    self.__lock.release()
                except:
                    self.__lock.break_lock()

    def __contains__(self, key: str):
        return key in self.__data

    def __getitem__(self, key: str):
        if self.__lock:
            with self.__lock:
                value = self.__data[key]
        else:
            value = self.__data[key]
        return value

    def __setitem__(self, key: str, value):
        if self.__lock:
            with self.__lock:
                self.__data[key] = value
                self.__data.sync()
        else:
            self.__data[key] = value
            self.__data.sync()

    def __delitem__(self, key: str):
        if self.__lock:
            with self.__lock:
                del self.__data[key]
                self.__data.sync()
        else:
            del self.__data[key]
            self.__data.sync()

    def __iter__(self):
        for i in self.__data:
            yield i

    def __len__(self):
        return len(self.__data)

    def get(self, key: str, default=None):
        if self.__lock:
            with self.__lock:
                if key in self.__data:
                    res = self.__data[key]
                else:
                    res = default
        else:
            if key in self.__data:
                res = self.__data[key]
            else:
                res = default
        return res

    def update_user(self, user: User):
        key = user.username
        if self.__lock:
            with self.__lock:
                self.__data[key] = user
                self.__data.sync()
        else:
            self.__data[key] = user
            self.__data.sync()

    def close(self):
        self.__data.close()
        if LOCKER:
            if self.__lock.i_am_locking():
                try:
                    self.__lock.release()
                except:
                    self.__lock.break_lock()
        self.__data = None


class Nauta:

    def __init__(self):
        self.__data = DataBase()
        self.__state = OFFLINE

    @staticmethod
    def parse_time(t):
        try:
            h,m,s = [int(x.strip()) for x in t.split(":")]
            return h * 3600 + m * 60 + s
        except:
            return 0

    @staticmethod
    def get_inputs(form_soup):
        form = {}
        for i in form_soup.find_all("input"):
            try:
                form[i["name"]] = i["value"]
            except KeyError:
                continue
        return form

    @staticmethod
    def verify(username: str, password: str):
        session = requests.Session()
        r = session.get("https://secure.etecsa.net:8443/")
        soup = bs4.BeautifulSoup(r.text, PARSER)

        form = Nauta.get_inputs(soup)
        action = "https://secure.etecsa.net:8443/EtecsaQueryServlet"
        form['username'] = username
        form['password'] = password
        r = session.post(action, form)
        soup = bs4.BeautifulSoup(r.text, PARSER)
        exp_node = soup.find(string=re.compile("expira[ct]i[óo]n"))
        if not exp_node:
            return False
        return True

    @staticmethod
    def fetch_usertime(username: str):
        session = requests.Session()
        r = session.get("https://secure.etecsa.net:8443/EtecsaQueryServlet?op=getLeftTime&op1={}".format(username))
        return r.text

    @staticmethod
    def fetch_expire_date(username, password):
        session = requests.Session()
        r = session.get("https://secure.etecsa.net:8443/")
        soup = bs4.BeautifulSoup(r.text, PARSER)

        form = Nauta.get_inputs(soup)
        action = "https://secure.etecsa.net:8443/EtecsaQueryServlet"
        form['username'] = username
        form['password'] = password
        r = session.post(action, form)
        soup = bs4.BeautifulSoup(r.text, PARSER)
        exp_node = soup.find(string=re.compile("expiración"))
        if not exp_node:
            return "**invalid credentials**"
        exp_text = exp_node.parent.find_next_sibling('td').text.strip()
        exp_text = exp_text.replace('\\', '')
        return exp_text

    def get_card(self, user: str, as_dict=False):
        if user in self.__data:
            cd = self.__data[user]
            if isinstance(cd, str):
                cd = self.__data[cd]
            try:
                self.time_left(cd.username, True)
                cd =  self.__data[cd.username]
            except Exception as e:
                # print(e)
                pass
            if as_dict:
                return cd.json()
            return cd
        return None

    def card_add(self, username: str, password: str, verify=True):
        if verify:
            try:
                vv = Nauta.verify(username, password)
            except requests.exceptions.ConnectionError:
                print("Looks like there is no connection now. Credentials can't be verify.")
                return False
            if not vv:
                print("Credentials seem incorrect.")
                return False
        self.__data[username] = User(username, password)
        if verify:
            self.time_left(username, True)
            self.expire_date(username, password)
        return True

    def card_add_alias(self, username: str, alias: str):
        if not(username in self.__data):
            print("Credentials seem incorrect.")
            return False
        if isinstance(self.__data[username], str):
            print("Credentials seem to be an alias.")
            return False
        self.__data[alias] = username
        dd = self.__data[username]
        dd.update_alias(alias, self.__data.update_user)
        return True

    def card_delete(self, card: str):
        if card in self.__data:
            cd = self.__data[card]
            if isinstance(cd, str):
                card = cd
                cd = self.__data[card]
            del self.__data[card]
            if cd.alias:
                try:
                    del self.__data[cd.alias]
                except:
                    pass

    def card_update_password(self, card: str, password: str):
        if card in self.__data:
            cd = self.__data[card]
            if isinstance(cd, str):
                card = cd
                cd = self.__data[card]
            cd.update_password(password, self.__data.update_user)

    def get_cards(self, as_dict=False):
        for i in self.__data:
            dat = self.__data[i]
            if isinstance(dat, str):
                continue
            if as_dict:
                yield dat.json()
            else:
                yield dat

    def get_alias(self):
        for i in self.__data:
            dat = self.__data[i]
            if isinstance(dat, str):
                yield (i, dat)

    def time_left(self, username, fresh=False, cached=False):
        now = time.time()
        card_info = self.__data.get(username)
        if card_info is None:
            return None
        username = card_info.username
        last_update = card_info.last_update
        if not cached:
            if (now - last_update > 60) or fresh:
                time_left = Nauta.fetch_usertime(username)
                last_update = time.time()
                if re.match(r'[0-9:]+', time_left):
                    card_info.update_time_left(time_left, self.__data.update_user)
                    card_info.update_last_update(last_update, self.__data.update_user)
        time_left = card_info.time_left
        if not time_left:
            time_left = '-'
        return time_left

    def expire_date(self, username, fresh=False, cached=False):
        # expire date computation won't depend on last_update
        # because the expire date will change very infrequently
        # in the case of rechargeable accounts and it will
        # never change in the case of non-rechargeable cards
        card_info = self.__data.get(username)
        if card_info is None:
            return None
        username = card_info.username
        if not cached:
            if (not card_info.expire_date) or fresh:
                password = card_info.password
                exp_date = Nauta.fetch_expire_date(username, password)
                card_info.update_expire_date(exp_date, self.__data.update_user)
        exp_date = card_info.expire_date
        return exp_date

    def up_gui(self, usern, callback=None):
        if not callback:
            def nothing(txt, opt=None):
                pass
            callback=nothing
        session = requests.Session()
        try:
            r = session.get("http://google.com")
        except requests.exceptions.ConnectionError:
            callback("Looks like there is no connection now.", WARNING)
            return 1

        soup = bs4.BeautifulSoup(r.text, PARSER)
        action = soup.form["action"]
        if ('google.com' in ''.join(r.cookies.list_domains()) and
            not 'secure.etecsa.net' in action):
            callback("Looks like you're already connected. Use 'nauta down' to log out.", WARNING)
            return 1

        user = self.__data.get(usern)
        if user is None:
            callback("Invalid card: {}".format(usern), ERROR)
            return 1
        password = user.password
        username = user.username

        tl = user.time_left
        callback("Using card {}. Time left: {}".format(username, tl), INFORMATION)
        log("Connecting with card {}. Time left on card: {}".format(username, tl))

        form = Nauta.get_inputs(soup)

        #pprint("Calling session.post:")
        #pprint({"action": action,
        #        "form": form})
        r = session.post(action, form)

        soup = bs4.BeautifulSoup(r.text, PARSER)
        #pprint("-------soup------")
        #pprint(soup)
        form_soup = soup.find("form", id="formulario")
        #pprint("-------form_soup------")
        #pprint(form_soup)
        action = form_soup["action"]
        #pprint("-------action------")
        #pprint(action)
        form = Nauta.get_inputs(form_soup)
        #print("form:", form)
        form['username'] = username
        form['password'] = password
        csrfhw = form['CSRFHW']
        wlanuserip = form['wlanuserip']
        last_attribute_uuid = ""
        try:
            last_attribute_uuid = open(ATTR_UUID_FILE, "r").read().strip()
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
        with open(LOGOUT_URL_FILE, "w") as f:
            f.write(guessed_logout_url + "\n")

        log("Attempting connection. Guessed logout url:", guessed_logout_url)
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
            callback("Log in failed :(", ERROR)
            return 1
        else:
            with open(ATTR_UUID_FILE, "w") as f:
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
            with open(LOGOUT_URL_FILE, "w") as f:
                f.write(logout_url + "\n")
            callback("Logged in successfully.",INFORMATION)
            log("Connected. Actual logout URL is: '{}'".format(logout_url))
            if logout_url == guessed_logout_url:
                log("Guessed it right ;)")
            else:
                log("Bad guess :(")
        return 0

    def up_cli(self, usern):
        session = requests.Session()
        try:
            r = session.get("http://google.com")
        except requests.exceptions.ConnectionError:
            print("Looks like there is no connection now.")
            return

        soup = bs4.BeautifulSoup(r.text, PARSER)
        action = soup.form["action"]
        if ('google.com' in ''.join(r.cookies.list_domains()) and
            not 'secure.etecsa.net' in action):
            print("Looks like you're already connected. Use 'nauta down' to log out.")
            return

        user = self.__data.get(usern)
        if user is None:
            print("Invalid card: {}".format(usern))
            return
        password = user.password
        username = user.username

        tl = user.time_left
        print("Using card {}. Time left: {}".format(username, tl))
        log("Connecting with card {}. Time left on card: {}".format(username, tl))

        form = Nauta.get_inputs(soup)

        #pprint("Calling session.post:")
        #pprint({"action": action,
        #        "form": form})
        r = session.post(action, form)

        soup = bs4.BeautifulSoup(r.text, PARSER)
        #pprint("-------soup------")
        #pprint(soup)
        form_soup = soup.find("form", id="formulario")
        #pprint("-------form_soup------")
        #pprint(form_soup)
        action = form_soup["action"]
        #pprint("-------action------")
        #pprint(action)
        form = Nauta.get_inputs(form_soup)
        #print("form:", form)
        form['username'] = username
        form['password'] = password
        csrfhw = form['CSRFHW']
        wlanuserip = form['wlanuserip']
        last_attribute_uuid = ""
        try:
            last_attribute_uuid = open(ATTR_UUID_FILE, "r").read().strip()
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
        with open(LOGOUT_URL_FILE, "w") as f:
            f.write(guessed_logout_url + "\n")

        log("Attempting connection. Guessed logout url:", guessed_logout_url)
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
            print("Log in failed :(")
        else:
            with open(ATTR_UUID_FILE, "w") as f:
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
            with open(LOGOUT_URL_FILE, "w") as f:
                f.write(logout_url + "\n")
            print("Logged in successfully. To logout, run 'nauta down'")
            print("or just hit Ctrl+C here, I'll stick around...")
            log("Connected. Actual logout URL is: '{}'".format(logout_url))
            if logout_url == guessed_logout_url:
                log("Guessed it right ;)")
            else:
                log("Bad guess :(")
            try:
                while True:
                    print("\rConnection time: {} ".format(
                        human_secs(int(time.time()) - login_time)
                    ), end="")
                    time.sleep(1)
                    if not os.path.exists(LOGOUT_URL_FILE):
                        break
            except KeyboardInterrupt:
                print("Got a Ctrl+C, logging out...")
                log("Got Ctrl+C. Attempting disconnect...")
                r = session.get(logout_url)
                print(r.text)

                now = int(time.time())
                log("Response to logout request: '{}'".format(r.text))
                log("Connection time:", human_secs(now - login_time))

                tl = self.time_left(username)
                print("Reported time left:", tl)
                log("Reported time left:", tl)

    def down(self):
        try:
            logout_url = open(LOGOUT_URL_FILE).read().strip()
        except FileNotFoundError:
            print("Connection seems to be down already. To connect, use 'nauta up'")
            return
        session = requests.Session()
        print("Logging out...")
        r = session.get(logout_url)
        print(r.text)
        if 'SUCCESS' in r.text:
            os.remove(LOGOUT_URL_FILE)

    def down_gui(self, callback=None):
        if not callback:
            def nothing(txt, opt=None):
                pass
            callback=nothing
        try:
            logout_url = open(LOGOUT_URL_FILE).read().strip()
        except FileNotFoundError:
            callback("Connection seems to be down already.", WARNING)
            return 1
        session = requests.Session()
        callback("Logging out...", INFORMATION)
        r = session.get(logout_url)
        callback(r.text, INFORMATION)
        if 'SUCCESS' in r.text:
            os.remove(LOGOUT_URL_FILE)
            return 0

    def get_url_down(self):
        try:
            logout_url = open(LOGOUT_URL_FILE).read().strip()
        except FileNotFoundError:
            print("Connection seems to be down already. To connect, use 'nauta up'")
            return
        return logout_url
