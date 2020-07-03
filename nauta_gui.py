import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QTextEdit, QDockWidget, QTabWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QTime
from PyQt5.QtWidgets import QComboBox, QLabel, QLineEdit, QLCDNumber
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtWidgets import QListWidget, QButtonGroup, QRadioButton
from PyQt5.QtWidgets import QInputDialog, QDialog, QCheckBox, QMessageBox
from PyQt5.QtCore import QObject
import qtawesome as qta
import requests
from nauta import Nauta, LogLevel
from nauta.exceptions import ConectionError, BadCredentials


LOG_COLORS = {LogLevel.INFORMATION: "green", LogLevel.WARNING: "orange", LogLevel.ERROR: "red",
              LogLevel.DEBUG: "blue", LogLevel.NAME: "black"}


def logcolor(txt, level):
    return "<font color=\""+LOG_COLORS[level]+"\">"+txt+"</font>"


def logsize(txt, size):
    return "<h"+str(size)+">"+txt+"</h"+str(size)+">"

def tr(txt):
    return txt

class NautaWrap:
    nauta = Nauta()
    def __init__(self):
        self._active=False
        self._used_account=None
        #self.nauta=Nauta()
        self.clock=None
        self._f_load_u_ntgui=None
        self._f_load_u_ugui=None

    def set_f_load_u_ntgui(self, callb):
        self._f_load_u_ntgui=callb

    def set_f_load_u_ugui(self, callb):
        self._f_load_u_ugui=callb

    def activate(self):
        self._active=True

    def set_account(self, acc):
        self._used_account=acc

    def deactivate(self):
        self._active=False

    def update_u(self):
        if self._f_load_u_ntgui:
            self._f_load_u_ntgui()
        if self._f_load_u_ugui:
            self._f_load_u_ugui()

    @property
    def active(self):
        return self._active

    @property
    def account(self):
        return self._used_account

class Logger(QObject):
    def __init__(self, name, signal):
        self._name = name
        self._signal = signal

    def emit(self, txt, num):
        self._signal.emit(self._name, txt, num)

    @property
    def signal(self):
        return self._signal

class DigitalClock(QLCDNumber):

    def __init__(self):
        super(DigitalClock, self).__init__(8)
        self.setSegmentStyle(QLCDNumber.Filled)
        self.timer = QTimer()
        self.timer.timeout.connect(self.showTime)
        self.time = QTime(0,0,0)
        text = self.time.toString("hh:mm:ss")
        self.display(text)

    def start(self):
        self.time = QTime(0,0,0)
        self.time.start()
        self.timer.start(1000)

    def stop(self):
        self.timer.stop()

    @pyqtSlot()
    def showTime(self):
        # print(self.time.elapsed())
        tt = QTime(0,0,0)
        tt = tt.addMSecs(self.time.elapsed())
        text = tt.toString("hh:mm:ss")
        # print(text)
        self.display(text)

class NautaGUI(QWidget):
    logginn = pyqtSignal(str, str, LogLevel)

    def __init__(self):
        super(NautaGUI, self).__init__()
        self.nautaw = NautaWrap()
        self.nautaw.set_f_load_u_ntgui(self.load_users)
        self.nauta = self.nautaw.nauta
        self.loggin = Logger('NautaGUI', self.logginn)

        self.cl = QVBoxLayout()

        self.cb = QComboBox()
        self.load_users()
        self.cl.addWidget(self.cb)

        tt2 = QVBoxLayout()
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Nombre de ususario:'))
        self.username = QLabel('')
        tt.addWidget(self.username)
        tt2.addLayout(tt)
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Tiempor restante:'))
        self.time_left = QLabel('')
        tt.addWidget(self.time_left)
        tt2.addLayout(tt)
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Fecha de expiración:'))
        self.expire_date = QLabel('')
        tt.addWidget(self.expire_date)
        tt2.addLayout(tt)
        self.cl.addLayout(tt2)

        self.clock = DigitalClock()
        self.cl.addWidget(self.clock)

        tt = QHBoxLayout()
        start = qta.icon(
            'mdi.play',
            color='green',
            color_active='yellow')
        self.start = QPushButton(start,"")
        stop = qta.icon(
            'mdi.stop',
            color='red',
            color_active='yellow')
        self.stop = QPushButton(stop,"")
        tt.addStretch()
        tt.addWidget(self.start)
        tt.addStretch()
        tt.addWidget(self.stop)
        tt.addStretch()
        self.cl.addLayout(tt)

        self.setLayout(self.cl)
        self.cb.activated.connect(self.choise)
        self.start.clicked.connect(self.up)
        self.stop.clicked.connect(self.down)
        if self.cb.count()!=0:
            self.choise(self.cb.currentIndex())

    def load_users(self):
        self.cb.clear()
        for i in sorted(self.nauta.get_cards(as_dict=True),key=lambda x: x['username']):
            self.cb.addItem(i['username'])
        #self.cb.repaint()

    def wraplog(self, txt, inf):
        self.loggin.emit(txt, inf)

    @pyqtSlot()
    def up(self):
        if self.cb.count()!=0:
            user = self.username.text()
            if self.nauta.up_gui(user, self.wraplog):
                return
            self.clock.start()
            self.nautaw.activate()

    @pyqtSlot()
    def down(self):
        if self.cb.count()!=0:
            if self.nauta.down_gui(self.wraplog):
                return
            self.clock.stop()
            self.nautaw.deactivate()

    @pyqtSlot(int)
    def choise(self, index):
        item = self.cb.itemText(index)
        data = self.nauta.get_card(item, as_dict=True)
        txt = 'Información de Usuario:'
        self.loggin.emit(txt, LogLevel.INFORMATION)
        tt = str(data['username'])
        self.nautaw.set_account(tt)
        txt = 'Nombre de ususario: '+tt
        self.username.setText(tt)
        self.loggin.emit(txt, LogLevel.INFORMATION)
        tt=str(data['time_left'])
        txt = 'Tiempo restante: '+tt
        self.time_left.setText(tt)
        self.loggin.emit(txt, LogLevel.INFORMATION)
        tt = str(data['expire_date'])
        txt = 'Fecha de expiración: '+tt
        self.expire_date.setText(tt)
        self.loggin.emit(txt, LogLevel.INFORMATION)

class UsersGUI(QWidget):

    logginn = pyqtSignal(str, str, LogLevel)

    def __init__(self):
        super(UsersGUI, self).__init__()
        self.loggin = Logger('UsersGUI', self.logginn)
        self.nautaw = NautaWrap()
        self.nautaw.set_f_load_u_ugui(self.load_users)
        self.nauta = self.nautaw.nauta

        self.cl = QVBoxLayout()

        self.li = QListWidget()
        self.load_users()
        self.cl.addWidget(self.li)

        tt = QHBoxLayout()
        addu = qta.icon(
            'mdi.account-plus',
            color='green',
            color_active='yellow')
        self.addu = QPushButton(addu,"")
        editu = qta.icon(
            'mdi.account-edit',
            color='blue',
            color_active='yellow')
        self.editu = QPushButton(editu,"")
        remu = qta.icon(
            'mdi.account-minus',
            color='red',
            color_active='yellow')
        self.remu = QPushButton(remu,"")
        tt.addWidget(self.addu)
        tt.addWidget(self.editu)
        tt.addWidget(self.remu)
        tt.addStretch()
        self.verif = QCheckBox("Verificar cuenta")
        tt.addWidget(self.verif)
        self.cl.addLayout(tt)

        self.setLayout(self.cl)

        self.addu.clicked.connect(self.adduser)
        self.editu.clicked.connect(self.edituser)
        self.remu.clicked.connect(self.deluser)

    def adduser(self):
        self.loggin.emit("Agregando cuenta.", LogLevel.INFORMATION)
        txt, ok = QInputDialog.getText(self, tr("Agregar Cuenta"),
                                            tr("Usuario"), 0, "")
        if not ok:
            self.loggin.emit("Operacion cancelada por el usuario.", LogLevel.INFORMATION)
            return
        user = txt
        txt, ok = QInputDialog.getText(self, tr("Agregar Cuenta"),
                                            tr("Contraseña"), 2, "")
        if not ok:
            self.loggin.emit("Operacion cancelada por el usuario.", LogLevel.INFORMATION)
            return
        passw = txt
        if self.verif.isChecked():
            try:
                self.loggin.emit("Verificando cuenta {0}.".format(user), LogLevel.INFORMATION)
                self.nauta.card_add(user, passw, verify=True, raise_exception=True)
            except ConectionError:
                self.loggin.emit("Parece que no hay connexion en este momento. No se puede verificar la cuenta. Desmarque verificar para poder agregarla.", LogLevel.WARNING)
                self.loggin.emit("No se pudo agregar la cuenta por que no se pudo verificar.", LogLevel.INFORMATION)
                return
            except BadCredentials:
                self.loggin.emit("Cuenta incorrecta.", LogLevel.WARNING)
                self.loggin.emit("No se pudo agregar la cuenta por que es incorrecta.", LogLevel.INFORMATION)
                return
            self.loggin.emit("Cuenta {0} agergada correctamente.".format(user), LogLevel.INFORMATION)
            self.nautaw.update_u()
            return
        self.nauta.card_add(user, passw, verify=False, raise_exception=False)
        self.loggin.emit("Cuenta {0} agergada correctamente.".format(user), LogLevel.INFORMATION)
        self.nautaw.update_u()

    def edituser(self):
        cc = self.li.currentItem()
        if not cc:
            return
        txt = cc.text()
        card=self.nauta.get_card(txt, try_update=False)
        userc = card.username
        passwc = card.password
        self.loggin.emit("Editando cuenta.", LogLevel.INFORMATION)
        txt, ok = QInputDialog.getText(self, tr("Editar Cuenta"),
                                            tr("Usuario"), 0, userc)
        if not ok:
            self.loggin.emit("Operacion cancelada por el usuario.", LogLevel.INFORMATION)
            return
        user = txt
        txt, ok = QInputDialog.getText(self, tr("Editar Cuenta"),
                                            tr("Contraseña"), 2, passwc)
        if not ok:
            self.loggin.emit("Operacion cancelada por el usuario.", LogLevel.INFORMATION)
            return
        passw = txt
        if self.verif.isChecked():
            self.loggin.emit("Verificando cuenta {0}.".format(user), LogLevel.INFORMATION)
            try:
                vv = self.nauta.verify(user, passw)
            except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                self.loggin.emit("Parece que no hay connexion en este momento. No se puede verificar la cuenta. Desmarque verificar para poder editarla.", LogLevel.WARNING)
                self.loggin.emit("No se pudo editar la cuenta por que no se pudo verificar.", LogLevel.INFORMATION)
                return
            if not vv:
                self.loggin.emit("Cuenta incorrecta.", LogLevel.WARNING)
                self.loggin.emit("No se pudo editar la cuenta por que es incorrecta.", LogLevel.INFORMATION)
                return
            card=self.nauta.get_card(txt, try_update=True)
            self.nauta.card_update(userc, card.to_json())
            self.loggin.emit("Cuenta {0} editada correctamente.".format(user), LogLevel.INFORMATION)
            self.nautaw.update_u()
            return
        self.nauta.card_update(userc, card.to_json())
        self.loggin.emit("Cuenta {0} editada correctamente.".format(user), LogLevel.INFORMATION)
        self.nautaw.update_u()

    def deluser(self):
        cc = self.li.currentItem()
        if not cc:
            return
        txt = cc.text()
        card=self.nauta.get_card(txt, try_update=False)
        userc = card.username
        self.loggin.emit("Eliminando cuenta.", LogLevel.INFORMATION)
        if self.nautaw.active and self.nautaw.account==userc:
            self.loggin.emit("Cuenta en uso. Es necesario desconnectarse primero.", LogLevel.INFORMATION)
            return
        ok = QMessageBox.question(self,"Eliminar cuenta","Seguro que quiere eliminar la cuenta {0}?".format(userc))
        if ok==QMessageBox.No:
            self.loggin.emit("Operacion cancelada por el usuario.", LogLevel.INFORMATION)
            return
        self.nauta.card_delete(userc)
        self.nautaw.update_u()

    def load_users(self):
        self.li.clear()
        for i in sorted(self.nauta.get_cards(as_dict=True), key=lambda x: x['username']):
            self.li.addItem(i['username'])


class Main(QMainWindow):

    def __init__(self):
        super(Main, self).__init__()
        self.tabw = QTabWidget(self)

        self.cw1 = NautaGUI()
        self.tabw.addTab(self.cw1,'Nauta')

        acc = qta.icon(
            'mdi.account',
            color='green',
            color_active='yellow')
        self.cw2 = UsersGUI()
        self.tabw.addTab(self.cw2,acc,"")

        #self.tabw.setTabShape(QTabWidget.Triangular)
        #self.tabw.setTabPosition(QTabWidget.West)
        self.setCentralWidget(self.tabw)
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logsdock = QDockWidget("Logs", self)
        self.logsdock.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.TopDockWidgetArea)
        self.logsdock.setWidget(self.logs)
        self.logsdock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.logsdock)
        self.cw1.logginn.connect(self.logger)
        self.cw2.logginn.connect(self.logger)
        self.tabw.currentChanged.connect(self.change)

    @pyqtSlot(str, str, LogLevel)
    def logger(self, name, txt, level):
        if self.logs.document().lineCount() > 1000:
            self.logs.clear()
        txtt = logcolor(name+': ', LogLevel.NAME)
        txtt += logcolor(txt, level)
        self.logs.append(txtt)

    @pyqtSlot(int)
    def change(self, index):
        if index == 0:
            self.cw1.load_users()

#if __name__ == '__main__':
import sys
import time
import traceback
from io import StringIO

def exceptio_hook(exectype, value, tracebackobj):
    logfile = 'exceptions.log'
    separator = '-' * 80
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")
    errmsg = '{0}: \n{1}'.format(str(exectype),str(value))
    tbinfile = StringIO()
    traceback.print_tb(tracebackobj, None, tbinfile)
    tbinfile.seek(0)
    tbininfo = tbinfile.read()
    sections = [separator,timeString,separator,errmsg,separator,tbininfo]
    msg='\n'.join(sections)
    with open(logfile,'w') as f:
        f.write(msg)
    errbox = QMessageBox()
    errbox.setText('Exception\n'+str(msg))
    errbox.exec_()
def main():
    sys.excepthook = exceptio_hook
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    w = Main()
    w.resize(784, 521)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()