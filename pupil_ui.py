# from PyQt5.QtGui import QPixmap, QImage         
# from PyQt5.QtWidgets import QWidget,QMainWindow, QLabel, QSizePolicy, QApplication, QAction, QHBoxLayout,QProgressBar
# from PyQt5.QtCore import Qt,QEvent,QObject
# from PyQt5.QtCore import *
# import sys,traceback

# import ctypes as C
# import numpy as np
# import cv2

# # Import PyhtonNet
# import clr
# # Load IC Imaging Control .NET 
# clr.AddReference('TIS.Imaging.ICImagingControl35')
# clr.AddReference('System')

# # Import the IC Imaging Control namespace.
# import TIS.Imaging
# from System import TimeSpan

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout

from PyQt5.QtCore import QCoreApplication, QDate, Qt, QTime
from PyQt5.QtGui import QFont


class pupil(QMainWindow, QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Pupilometry')
        self._windowsize()
        self._windowcenter()
        self.statusBar().showMessage('Initialize')

        okButton = QPushButton('OK', self)
        cancelButton = QPushButton('Cancel', self)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)
        hbox.addStretch(1)
        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        
        vbox.addStretch(1)
        print('asdf')

        
        self._tooltips()
        self._quitButton()
        self._menubar()
        self._toolbar()

        self.show()
    

    def _windowsize(self):
        # self.setGeometry(300, 300, 400, 400) # (x, y, width, height) of window
        # top left=(0, 0)
        # as go from left to right, x increases
        # as go from top to bottom, y increases
        self.height = 500
        self.width = 500
        self.resize(self.width, self.height)

    def _windowcenter(self):
        window_geometry = self.frameGeometry()
        monitor_center = QDesktopWidget().availableGeometry().center()
        window_geometry.moveCenter(monitor_center)
        self.move(window_geometry.topLeft())

    def _tooltips(self):
        QToolTip.setFont(QFont('Airal', 10))
        # self.setToolTip('<b>QWidget<b> widget')
    
    def _quitButton(self):
        quit = QPushButton('Quit', self)
        quit.move(int(self.width*0.75), int(self.height*0.9))
        quit.resize(quit.sizeHint())
        quit.setToolTip('<b>QPushButton<b> widget')
        quit.clicked.connect(QCoreApplication.instance().quit)



        

    def _menubar(self):
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)

        self.fileMenu = self.mainMenu.addMenu('&File')
        self.fileMenu.addAction(self._exitaction())

    def _toolbar(self):
        self.toolbar = self.addToolBar('Exit')
        self.toolbar.addAction(self._exitaction(shortcut=False))

    def _exitaction(self, shortcut=True):
        # 카메라가 연결된 경우 동작을 중지하고 끄는것 추가
        exitAction = QAction('Exit', self)
        if shortcut:
            exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit Application')
        exitAction.triggered.connect(qApp.quit)
        return exitAction
    

if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())