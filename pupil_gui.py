import sys
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QBoxLayout, QSplitter, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout, QLabel
from PyQt5.QtCore import QCoreApplication, QDate, Qt, QTime
from PyQt5.QtGui import QFont


class pupil(QMainWindow):
    def __init__(self, height=500, width=500):
        super().__init__()
        self.height = 800
        self.width = 1300
        
        self.initUI()
        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)

    def initUI(self):
        self.setWindowTitle('Pupilometry')
        self._windowsize()
        self._windowcenter()
        self.statusBar().showMessage('Initialize')
        self._tooltips()
        self._menubar()
        # self._toolbar()
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

    # def _toolbar(self):
    #     self.toolbar = self.addToolBar('Exit')
    #     self.toolbar.addAction(self._exitaction(shortcut=False))

    # 카메라가 연결된 경우 동작을 중지하고 끄는것 추가
    def _exitaction(self, shortcut=True):
        exitAction = QAction('Exit', self)
        if shortcut:
            exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit Application')
        exitAction.triggered.connect(qApp.quit)
        return exitAction
    

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QHBoxLayout()
        
        self._set_movie_frame()
        self._set_graph_frame()
        self._set_interactive_frmae()
        self._main_division()

        self.setLayout(self.main_layout)

        self._add_movie_widget()

    def _add_movie_widget(self):
        label1 = QLabel()
        label1.setText('movie')
        label2 = QLabel()
        label2.setText('display')
        live_bt = QPushButton('live')
        stop_bt = QPushButton('stop')

        self.movie_layout.addWidget(label1, alignment=Qt.AlignTop)
        self.movie_layout.addWidget(label2, alignment=Qt.AlignVCenter)
        self.movie_layout.addWidget(live_bt, alignment=Qt.AlignBottom)
        self.movie_layout.addWidget(stop_bt, alignment=Qt.AlignBottom)

    def _set_movie_frame(self): 
        '''
        frame for pupil live imaging
        '''
        self.movie_frame = QFrame()
        self.movie_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.movie_layout = QHBoxLayout()
        self.movie_frame.setLayout(self.movie_layout)

    def _set_graph_frame(self):
        '''
        frame for dynamic plot of pupil size
        '''
        self.graph_frame = QFrame()
        self.graph_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.graph_layout = QGridLayout()
        self.graph_frame.setLayout(self.graph_layout)

    def _set_interactive_frmae(self):
        self.interactive_frame = QFrame()
        self.interactive_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.interactive_layout = QHBoxLayout()
        self.interactive_frame.setLayout(self.interactive_layout)

    def _main_division(self):
        '''
        Make splitter for dividing main window
        '''
        self.splt1 = QSplitter(Qt.Vertical)
        self.splt2 = QSplitter(Qt.Horizontal)  
        
        self.splt1.addWidget(self.movie_frame)
        self.splt1.addWidget(self.graph_frame)
        self.splt2.addWidget(self.splt1)
        self.splt2.addWidget(self.interactive_frame)
        
        self.splt2.setSizes([400, 100])
        self.splt1.setSizes([100, 100])
        self.main_layout.addWidget(self.splt2)

        
        
if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())