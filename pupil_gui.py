import sys
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QBoxLayout, QSplitter, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout
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
        # self.setCentralWidget(SetWidget())
        self.setCentralWidget(MainLayout())
        # self.setLayout(MainLayout())


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
    
    # def _widget_layout(self):
    #     main_layout = QGroupBox('asdf')

    #     video_frame = QFrame()
    #     video_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
    #     frame_2 = QFrame()
    #     frame_2.setFrameShape(QFrame.Panel | QFrame.Sunken)
        
    #     layout_1 = QVBoxLayout()
    #     layout_2 = QVBoxLayout()

    #     button_1 = QPushButton("button_1")
    #     button_2 = QPushButton("button_2")

    #     layout_1.addWidget(button_1)
    #     layout_2.addWidget(button_2)

    #     video_frame.setLayout(layout_1)
    #     frame_2.setLayout(layout_2)

    #     main_layout.addWidget(video_frame)
    #     main_layout.addWidget(frame_2)

    #     # wg = QWidget()
    #     # wg.setLayout(main_layout)
    #     return video_frame


class MainLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QHBoxLayout()
        
        self._set_movie_frame()
        self._set_graph_frame()
        self._set_interactive_frmae()
        self._main_division()

        self.setLayout(self.main_layout)

    def _set_movie_frame(self):
        '''
        frame for pupil live imaging
        '''
        self.movie_frame = QFrame()
        self.movie_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.movie_layout = QGridLayout()
        
        # add widget in this section, tmp
        button_1 = QPushButton("button_1")
        self.movie_layout.addWidget(button_1)

        self.movie_frame.setLayout(self.movie_layout)

    def _set_graph_frame(self):
        '''
        frame for dynamic plot of pupil size
        '''
        self.graph_frame = QFrame()
        self.graph_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.graph_layout = QGridLayout()

        # add widget in this section, tmp
        button_2 = QPushButton("button_2")
        self.graph_layout.addWidget(button_2)

        self.graph_frame.setLayout(self.graph_layout)

    def _set_interactive_frmae(self):
        self.interactive_frame = QFrame()
        self.interactive_frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        self.interactive_layout = QHBoxLayout()

        # add widget in this section, tmp
        button_3 = QPushButton("button_3")
        self.interactive_layout.addWidget(button_3)

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

        

        self.main_layout.addWidget(self.splt2)
        self.splt1.setSizes([1, 1])
        self.splt2.setSizes([3, 1])
        
if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())