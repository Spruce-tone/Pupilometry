import sys
import os
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QBoxLayout, QSplitter, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout, QLabel, QGroupBox
from PyQt5.QtCore import QCoreApplication, QDate, Qt, QTime, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes

from lib.SignalConnection import LiveDisplay



class pupil(QMainWindow):
    def __init__(self, height=500, width=500):
        super().__init__()
        self.height = 1400
        self.width = 1600
        
        # define main widget
        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)

        # define camera handle and functions
        self.ic = self.main_widget.ic
        self.camera = self.main_widget.camera

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Pupilometry')
        self._windowsize()
        self._windowcenter()
        self.statusBar().showMessage('Initialize')
        self._tooltips()
        self._menubar()
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

        # File menu
        self.fileMenu = self.mainMenu.addMenu('&File')
        
        # Exit menue
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self._exitaction)
        self.fileMenu.addAction(exitAction)

        # select device menu
        selectDeviceAction = QAction('Select Device', self)
        selectDeviceAction.triggered.connect(self._selectdevice)
        self.fileMenu.addAction(selectDeviceAction)

    def _selectdevice(self):
        self.ic.IC_StopLive(self.camera)
        self.ic.IC_ShowDeviceSelectionDialog(None)

        if self.ic.IC_IsDevValid(self.camera):
            self.ic.IC_StartLive(self.camera, 0)
            self.ic.IC_SaveDeviceStateToFile(self.camera, b'device.xml')

    def _exitaction(self):
        if self.ic.IC_IsDevValid(self.camera):
            self.ic.IC_StopLive(self.camera)
            self.ic.IC_ReleaseGrabber(self.camera)
        qApp.quit()


        # def _toolbar(self):
    #     self.toolbar = self.addToolBar('Exit')
    #     self.toolbar.addAction(self._exitaction(shortcut=False))    

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # initialize and connect camera
        self._init_camera()

        # Define main layout
        self.main_layout = QHBoxLayout()
        
        # Generate and assign the frame layout
        self._generate_frames()
        self._main_division()

        # set main layout
        self.setLayout(self.main_layout)

        self._add_movie_widget()
        self._add_control_panel_widget()

    def _init_camera(self):
        '''
        initialize and connect camera
        '''
        self.ic = ctypes.cdll.LoadLibrary('./lib/tisgrabber_x64.dll')
        tis.declareFunctions(self.ic)
        self.ic.IC_InitLibrary(0)
        self.camera = tis.openDevice(self.ic)

    # Movie widget 만들기
    def _add_movie_widget(self):
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.label.resize(720, 1080)

        self.live = LiveDisplay(self, self.camera, self.ic)
        self.live.start()
        self.live.Pixmap_display.connect(self.display_image)  
        self.movie_layout.addWidget(self.label)

    # control pannel widget
    def _add_control_panel_widget(self):
        self.state_panel = QGroupBox('Status')
        self.state_panel.setFont(QFont('Arial', 10))


        self.file_panel = QGroupBox('Files')
        self.file_panel.setFont(QFont('Arial', 10))

        # imaging control
        self.imaging_control = QGroupBox('Imaging control')
        self.imaging_control.setFont(QFont('Arial', 10))
        self.imaging_control_layout = QVBoxLayout()

        live_imaging = QPushButton('Live')
        stop_imaging = QPushButton('Stop')
        ready_trigger = QPushButton('Set trigger')
        self._add_multiple_widget(self.imaging_control_layout, [live_imaging, stop_imaging, ready_trigger])
        self.imaging_control.setLayout(self.imaging_control_layout)

        live_imaging.clicked.connect(self._resume_live_imaging)
        stop_imaging.clicked.connect(self._stop_live_imaging)
        

        # Control panel ratio
        self.control_panel_layout.addWidget(self.state_panel, 2)
        self.control_panel_layout.addWidget(self.file_panel, 4)
        self.control_panel_layout.addWidget(self.imaging_control, 2)

    def _add_multiple_widget(self, layout : QBoxLayout, widgets : List):
        for widget in widgets:
            layout.addWidget(widget)

    def _set_frame(self, layout):
        '''
        define frames
        '''
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel | QFrame.Raised)
        frame_layout = layout
        frame.setLayout(frame_layout)
        return frame, frame_layout

    def _generate_frames(self):
        '''
        generate frames to use
        '''
        self.movie_frame, self.movie_layout = self._set_frame(QGridLayout())
        self.graph_frame, self.graph_layout = self._set_frame(QGridLayout())
        self.control_panel_frame, self.control_panel_layout = self._set_frame(QVBoxLayout())

    def _main_division(self):
        '''
        Make splitter for dividing main window
        '''
        self.splt1 = QSplitter(Qt.Vertical)
        self.splt2 = QSplitter(Qt.Horizontal)  
        
        self.splt1.addWidget(self.movie_frame)
        self.splt1.addWidget(self.graph_frame)
        self.splt2.addWidget(self.splt1)
        self.splt2.addWidget(self.control_panel_frame)
        
        self.splt2.setSizes([250, 100])
        self.splt1.setSizes([100, 100])
        self.main_layout.addWidget(self.splt2)
    
    @pyqtSlot(QImage)
    def display_image(self, qimage):
        self.live_pixmap = QPixmap.fromImage(qimage)
        self.live_pixmap.scaled(720, 470, Qt.KeepAspectRatioByExpanding)
        self.label.setPixmap(self.live_pixmap)
    
    def _resume_live_imaging(self):
        self.live.resume()
        self.live.start()

    def _stop_live_imaging(self):
        self.live.pause()


if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())


         # movie_status = QLabel('Pupil display')
        # movie_status.setFont(QFont('Arial', 15))
        # self.movie_layout.addWidget(movie_status, alignment=Qt.AlignHCenter)
        # self.movie_layout.addWidget(label2, alignment=Qt.AlignTop)
        # self.movie_layout.addWidget(self.label, alignment=Qt.AlignHCenter)
        # self.movie_layout.addWidget(live_bt, alignment=Qt.AlignBottom)
        # self.movie_layout.addWidget(stop_bt, alignment=Qt.AlignBottom)
