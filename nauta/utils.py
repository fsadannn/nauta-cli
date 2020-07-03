import re
from typing import Optional, Union
from parsel import Selector
from requests import Session
try:
    from .constants import CONFIG
except ImportError:
    from constants import CONFIG

verif_pattern = re.compile("expira[ct]i[óo]n", re.IGNORECASE)
credit = re.compile("cr[eé]dito?", re.IGNORECASE)

def get_inputs(page: Union[Selector, str]):
    if isinstance(page, str):
        page = Selector(text=page)
    form_page = page.css('form')[-1]
    form = {}
    for i in form_page.css('input'):
        if i.attrib.get('type') and i.attrib.get('type')=="button":
            continue
        try:
            form[i.attrib["name"]] = i.attrib["value"]
        except KeyError:
            continue
    return form

def verify(username: str, password: str, session:Optional[Session]=None):
    if session is None:
        session = Session()
        session.headers['User-Agent']=CONFIG['USER_AGENT']
    r = session.get("https://secure.etecsa.net:8443/")

    form = get_inputs(r)
    action = "https://secure.etecsa.net:8443/EtecsaQueryServlet"
    form['username'] = username
    form['password'] = password
    r = session.post(action, form)
    sel = Selector(r.text)
    exp_node = sel.re_first(verif_pattern)
    if exp_node is None:
        return False
    return True

def get_info(username: str, password: str, session:Optional[Session]=None):
    if session is None:
        session = Session()
        session.headers['User-Agent']=CONFIG['USER_AGENT']
    r = session.get("https://secure.etecsa.net:8443/")
    form = get_inputs(r)
    action = "https://secure.etecsa.net:8443/EtecsaQueryServlet"
    form['username'] = username
    form['password'] = password
    r = session.post(action, form)
    sel = Selector(r.text)
    exp_node = sel.re_first(verif_pattern)
    if exp_node is None:
        return "**invalid credentials**"
    res = {}
    table = sel.css('table')[0]
    table = table.css('td')
    for i, j in zip(table.css('td')[::2],table.css('td')[1::2]):
        if verif_pattern.search(i.css("::text").get().strip()):
            res['expiration']=j.css("::text").get().strip()
        if credit.search(i.css("::text").get().strip()):
            res['credit']=j.css("::text").get().strip()
    cr = float(res['credit'].split(' ')[0])
    res['time_left'] = cr/CONFIG['TIME_CONVERSION_CONSTANT']
    return res

def human_secs(secs):
    return "{:02.0f}:{:02.0f}:{:02.0f}".format(
        secs // 3600,
        (secs % 3600) // 60,
        secs % 60,
    )
