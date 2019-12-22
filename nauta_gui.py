from nauta import Nauta
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QTextEdit, QDockWidget, QTabWidget
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QTime
from PyQt5.QtWidgets import QComboBox, QLabel, QLineEdit, QLCDNumber
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton

INFORMATION = 0
WARNING = 1
ERROR = 2
DEBUG = 3
NAME = 4

LOG_COLORS = {INFORMATION: "green", WARNING: "orange", ERROR: "red",
              DEBUG: "blue", NAME: "black"}


def logcolor(txt, level):
    return "<font color=\""+LOG_COLORS[level]+"\">"+txt+"</font>"


def logsize(txt, size):
    return "<h"+str(size)+">"+txt+"</h"+str(size)+">"

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
    logginn = pyqtSignal(str, int)

    def __init__(self):
        super(NautaGUI, self).__init__()
        self.nauta = Nauta()

        self.cl = QVBoxLayout()

        self.cb = QComboBox()
        for i in self.nauta.get_cards(True):
            self.cb.addItem(i['username'])
        self.cl.addWidget(self.cb)

        tt2 = QVBoxLayout()
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Username'))
        self.username = QLabel('')
        tt.addWidget(self.username)
        tt2.addLayout(tt)
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Time_left'))
        self.time_left = QLabel('')
        tt.addWidget(self.time_left)
        tt2.addLayout(tt)
        tt = QHBoxLayout()
        tt.addWidget(QLabel('Expire_date'))
        self.expire_date = QLabel('')
        tt.addWidget(self.expire_date)
        tt2.addLayout(tt)
        self.cl.addLayout(tt2)

        self.clock = DigitalClock()
        self.cl.addWidget(self.clock)

        tt = QHBoxLayout()
        self.start = QPushButton('Start')
        self.stop = QPushButton('Stop')
        tt.addWidget(self.start)
        tt.addWidget(self.stop)
        self.cl.addLayout(tt)

        self.setLayout(self.cl)
        self.cb.activated.connect(self.choise)
        self.start.clicked.connect(self.up)
        self.stop.clicked.connect(self.down)
        if self.cb.count()!=0:
            self.choise(self.cb.currentIndex())

    def wraplog(self, txt, inf):
        self.logginn.emit(txt, inf)

    @pyqtSlot()
    def up(self):
        if self.cb.count()!=0:
            user = self.username.text()
            if self.nauta.up_gui(user, self.wraplog):
                return
            self.clock.start()

    @pyqtSlot()
    def down(self):
        if self.cb.count()!=0:
            if self.nauta.down_gui(self.wraplog):
                return
            self.clock.stop()

    @pyqtSlot(int)
    def choise(self, index):
        item = self.cb.itemText(index)
        data = self.nauta.get_card(item, True)
        txt = 'User Info:'
        self.logginn.emit(txt, INFORMATION)
        tt = str(data['username'])
        txt = 'username: '+tt
        self.username.setText(tt)
        self.logginn.emit(txt, INFORMATION)
        tt=str(data['time_left'])
        txt = 'time_left: '+tt
        self.time_left.setText(tt)
        self.logginn.emit(txt, INFORMATION)
        tt = str(data['expire_date'])
        txt = 'expire_date: '+tt
        self.expire_date.setText(tt)
        self.logginn.emit(txt, INFORMATION)


class Main(QMainWindow):

    def __init__(self):
        super(Main, self).__init__()
        self.cw = NautaGUI()

        self.setCentralWidget(self.cw)
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        self.logsdock = QDockWidget("Logs", self)
        self.logsdock.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.TopDockWidgetArea)
        self.logsdock.setWidget(self.logs)
        self.logsdock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.logsdock)
        self.cw.logginn.connect(self.logger)

    @pyqtSlot(str, int)
    def logger(self, txt, level):
        if self.logs.document().lineCount() > 1000:
            self.logs.clear()
        txtt = logcolor(txt, level)
        self.logs.append(txtt)


#if __name__ == '__main__':

app = QApplication(sys.argv)
app.setStyle('Fusion')
w = Main()
w.resize(784, 521)
w.show()
sys.exit(app.exec_())
