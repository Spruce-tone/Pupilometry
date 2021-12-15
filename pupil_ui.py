# from PyQt5.QtGui import QPixmap, QImage         
# from PyQt5.QtWidgets import QWidget,QMainWindow,\
#           QLabel, QSizePolicy, QApplication, \
#           QAction, QHBoxLayout,QProgressBar
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
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout

from PyQt5.QtCore import QCoreApplication, QDate, Qt, QTime
from PyQt5.QtGui import QFont



class SetWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.box_layout((1, 0, 1, 0), [self._quitButton()])

    def box_layout(self, position: Tuple[int], widgets: List[QPushButton]):
        left, right, top, bottom = position
        
        hbox = QHBoxLayout()
        hbox.addStretch(left)
        for widget in widgets:
            hbox.addWidget(widget)
        hbox.addStretch(right)
        
        vbox = QVBoxLayout()
        vbox.addStretch(top)
        vbox.addLayout(hbox)
        vbox.addStretch(bottom)
        self.setLayout(vbox)
        
    def _quitButton(self):
        quit = QPushButton('Quit', self)
        quit.setToolTip('<b>QPushButton<b> widget')
        quit.clicked.connect(QCoreApplication.instance().quit)
        return quit
    

class pupil(QMainWindow):
    def __init__(self, height=500, width=500):
        super().__init__()
        self.height = 500
        self.width = 500
        
        self.initUI()
        self.setCentralWidget(SetWidget())


    def initUI(self):
        self.setWindowTitle('Pupilometry')
        self._windowsize()
        self._windowcenter()
        self.statusBar().showMessage('Initialize')
        self._tooltips()
        self._menubar()
        self._toolbar()
        self.show()

    def _windowsize(self):
        # self.setGeometry(300, 300, 400, 400) # (x, y, width, height) of window
        # top left=(0, 0)
        # as go from left to right, x increases
        # as go from top to bottom, y increases
        self.resize(self.width, self.height)

    def _windowcenter(self):
        window_geometry = self.frameGeometry()
        monitor_center = QDesktopWidget().availableGeometry().center()
        window_geometry.moveCenter(monitor_center)
        self.move(window_geometry.topLeft())

    def _tooltips(self):
        QToolTip.setFont(QFont('Airal', 10))
        # self.setToolTip('<b>QWidget<b> widget')

    def _menubar(self):
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)

        self.fileMenu = self.mainMenu.addMenu('&File')
        self.fileMenu.addAction(self._exitaction())

    def _toolbar(self):
        self.toolbar = self.addToolBar('Exit')
        self.toolbar.addAction(self._exitaction(shortcut=False))

    # 카메라가 연결된 경우 동작을 중지하고 끄는것 추가
    def _exitaction(self, shortcut=True):
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