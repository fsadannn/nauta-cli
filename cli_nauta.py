import fire
from nauta import Nauta

class CLI:

    def __init__(self):
        self.nauta = Nauta()

    def up(self, user: str):
        self.nauta.up_cli(user)

    def down(self):
        self.nauta.down()

    def info(self, user):
        res = self.nauta.get_card(user, as_dict=True)
        if res is None:
            return 'User not in data.'
        return res

    def add(self, username, passord, verif: bool=True):
        self.nauta.card_add(username, passord, bool(verif))

    def cards(self):
        return list(self.nauta.get_cards(as_dict=True))

    def delete(self, name):
        self.nauta.card_delete(name)

    def aliases(self):
        return list(self.nauta.get_alias())

    def add_alias(self, username, alias):
        self.nauta.card_add_alias(username, alias)

    def url(self):
        return self.nauta.get_url_down()

def cli_f():
    return fire.Fire(CLI)

if __name__ == "__main__":
    fire.Fire(CLI)