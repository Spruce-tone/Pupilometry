import sys
import os
import shutil
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QBoxLayout, QDialog, QFileDialog, QFileSystemModel, \
                            QInputDialog, QSplitter, QTreeView, QTreeWidget, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout, QLabel, QGroupBox, QTextEdit, \
                            QLineEdit, QAbstractItemView, QTreeWidgetItem, \
                            QMessageBox
from PyQt5.QtCore import QCoreApplication, QDate, QItemSelectionModel, Qt, \
                        QTime, pyqtSignal, QThread, pyqtSlot, QItemSelection, \
                        QDir
from PyQt5.QtGui import QFont, QPixmap, QImage, QDoubleValidator, QKeyEvent
from lib import tisgrabber as tis
import numpy as np
import ctypes

sys.path.append('./lib')
from lib.SignalConnection import LiveDisplay, RefreshDevState
from lib.Automation.BDaq.InstantDiCtrl import InstantDiCtrl



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
        self._main_windowsize()
        self._windowcenter()
        self.statusBar().showMessage('Initialize')
        self._menubar()
        self.show()

    def _main_windowsize(self):
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

    def _menubar(self):
        self.mainMenu = self.menuBar()
        self.mainMenu.setNativeMenuBar(False)

        # File menu
        self.fileMenu = self.mainMenu.addMenu('&File')

        # select device menu
        selectDeviceAction = QAction('Select Device', self)
        selectDeviceAction.triggered.connect(self._selectdevice)
        self.fileMenu.addAction(selectDeviceAction)
        
        # Exit menue
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self._exitaction)
        self.fileMenu.addAction(exitAction)

    def _selectdevice(self):
        self.ic.IC_StopLive(self.main_widget.camera)
        self.ic.IC_ShowDeviceSelectionDialog(None)
 
        if self.ic.IC_IsDevValid(self.main_widget.camera):
            self.ic.IC_StartLive(self.main_widget.camera, 0)
            self.ic.IC_SaveDeviceStateToFile(self.camera, b'device.xml')

    def _exitaction(self):
        if self.ic.IC_IsDevValid(self.main_widget.camera):
            self.ic.IC_StopLive(self.main_widget.camera)
            self.ic.IC_ReleaseGrabber(self.main_widget.camera)
        self.main_widget.refresh_dev.stop()
        self.main_widget.live.stop()
        qApp.quit()


class FileTreeView(QTreeView):
    key_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.model = QFileSystemModel()
        self.model.setRootPath(os.getcwd())
        self.setModel(self.model)
        self.model.setReadOnly(False)
        self.setRootIndex(self.model.index(os.getcwd()))
        self.current_dir = os.getcwd()

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.index = []
        self.selectionModel().selectionChanged.connect(self._setIndex)
        self.doubleClicked.connect(self._move_dir)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:
            self._delete()

    @pyqtSlot()
    def _setIndex(self):
        self.index = [index for index in self.selectedIndexes() if index.column()==0]

    @pyqtSlot()
    def _rename(self):
        if len(self.index) == 1:
            self.index = self.index[0]
            os.chdir(self.model.filePath(self.model.parent(self.index)))
            fname = self.model.fileName(self.index)
            new_name, res = QInputDialog.getText(self, 'Rename', 'Enter the name to change',
                                QLineEdit.Normal, fname)

            if res: # if select OK button, res = True 
                while True:
                    duplicate_check = True
                    for file in os.listdir(os.getcwd()):
                        if file==new_name:
                            new_name, res = QInputDialog.getText(self, 'This name already exists', 
                                                                'Enter the name to change',
                                                                QLineEdit.Normal, new_name)

                            if not res:
                                return
                            duplicate_check = False
                    if duplicate_check:
                        break
                os.rename(fname, new_name)
            
            os.chdir(self.current_dir)

    @pyqtSlot()
    def _delete(self):
        if len(self.index) > 0:
            reply = QMessageBox.question(self, 'Warning!', 'Are you sure to remove this files or directories?',
                    QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                indexes = [idx for idx in self.index if self.model.parent(idx) not in self.index]

                for idx in indexes:
                    os.chdir(self.model.filePath(self.model.parent(idx)))
                    fname = self.model.fileName(idx)
                    try:
                        if self.model.isDir(idx):
                            shutil.rmtree(fname)
                        else:
                            os.unlink(fname)
                    except:
                        QMessageBox.about(self, 'Error!', f'You can''t remove "{fname}"')

            os.chdir(self.current_dir)

    @pyqtSlot()
    def _mvoe_parent_dir(self):
        self.setRootIndex(self.model.index(os.path.dirname(self.current_dir)))
        self.current_dir = os.path.dirname(self.current_dir)

    @pyqtSlot()
    def _move_dir(self):
        idx = self.index[0]

        if len(self.index)==1 and self.model.isDir(idx):
            self.setRootIndex(self.model.index(os.path.join(self.current_dir, idx.data())))
            self.current_dir = os.path.join(self.current_dir, idx.data())

    @pyqtSlot()
    def _file_browser(self):
        self.current_dir =  QFileDialog.getExistingDirectory(self)
        self.setRootIndex(self.model.index(self.current_dir))

    @pyqtSlot()
    def _mkdir(self):
        if len(self.index) >= 2:
            return
        else:
            if len(self.index)==0:
                parent = self.model.index(self.current_dir)
            elif len(self.index)==1:
                if self.model.isDir(self.index[0]):
                    parent = self.index[0]
                else:
                    parent = self.model.index(self.current_dir)

            fname = 'New dir'
            new_name, res = QInputDialog.getText(self, 'Make directory', 'Enter the name for new directory',
                                    QLineEdit.Normal, fname)

            if res: # if select OK button, res = True
                while True:
                    duplicate_check = True
                    for file in os.listdir(self.model.filePath(parent)):
                        if file==new_name:
                            new_name, res = QInputDialog.getText(self, 'This name already exists', 
                                                                'Enter another name for new directory',
                                                                QLineEdit.Normal, new_name)
                            if not res:
                                return
                            duplicate_check = False
                    if duplicate_check:
                        break
                self.model.mkdir(parent, new_name)
            
class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # initialize and connect camera
        self._init_camera()

        # initialize and connect trigger device
        self._init_trigger()

        # Define main layout
        self.main_layout = QHBoxLayout()
        
        # Generate and assign the frame layout
        self._generate_frames()
        self._main_division()

        # set main layout
        self.setLayout(self.main_layout)

        # movie display
        self._add_movie_widget()
        

        '''
        control panel division
        '''
        # device connection state
        self._dev_connection_state_widget()
        # tree view widget for file system   
        self._file_system_viewer()
        # imaging control panel
        self._imaging_control_panel()
        # assign ratio for control panel division 
        self._divide_control_panel()

    def _init_camera(self):
        '''
        initialize and connect camera
        '''
        # load library for camera control
        self.ic = ctypes.cdll.LoadLibrary('./lib/tisgrabber_x64.dll')
        tis.declareFunctions(self.ic)
        self.ic.IC_InitLibrary(0)

        # connect camera
        self.camera = tis.openDevice(self.ic)
        self.frame_rate = 29.97
    
    def _init_trigger(self):
        '''
        trigger device description, adventech usb-4751L
        '''
        self.dev_description = "USB-4751L,BID#0"
        self.startPort = 2
        self.portCount = 1

        try:
            self.trig = InstantDiCtrl(self.dev_description)
            print('exist trig')
        except:
            self.trig = None
            print('No trig')

    # movie widget
    def _add_movie_widget(self):
        '''
        generate movie widget
        connect widget to qthread for live imaging
        '''
        # generate display widget
        self.display_label = QLabel(self)
        self.display_label.setScaledContents(True)
        self.display_label.resize(720, 1080)

        # generate thread and connect to display widget
        self.live = LiveDisplay(self)
        self.live.start()
        self.live.Pixmap_display.connect(self.display_image)  
        self.movie_layout.addWidget(self.display_label)
    
    # device connection state
    def _dev_connection_state_widget(self):
        '''
        Panel for hardware connection state 
        '''
        self.state_panel = QGroupBox('Device connection state')
        self.state_panel.setFont(QFont('Arial', 12))
        self.state_panel_layout = QGridLayout()
        
        # define connection state label
        self.camera_connection_label = QLabel('Camera connection state ')
        self.camera_connection_state_label = QLabel('Ready')
        self.camera_connection_led = QLabel(self)
        self.camera_connection_led.setStyleSheet("QLabel {background-color : red; \
                                                    border-color : black; \
                                                    border-style : default; \
                                                    border-width : 0px; \
                                                    border-radius : 19px; \
                                                    min-height: 3px; \
                                                    min-width: 5px}")
        self.trig_connection_label = QLabel('Trigger device connection state ')
        self.trig_connection_state_label = QLabel('Ready')
        self.trig_connection_led = QLabel(self)
        self.trig_connection_led.setStyleSheet("QLabel {background-color : red; \
                                                    border-color : black; \
                                                    border-style : default; \
                                                    border-width : 0px; \
                                                    border-radius : 19px; \
                                                    min-height: 3px; \
                                                    min-width: 5px}")

        # Define signla thread
        self.refresh_dev = RefreshDevState(self)
        self.refresh_dev.start()
        self.refresh_dev.refresh_dev_state.connect(self._connection_state_view)

        # set device connection state viewer
        self.state_panel_layout.addWidget(self.camera_connection_label, 0, 0, 1, 5)
        self.state_panel_layout.addWidget(self.camera_connection_state_label, 0, 5, 1, 4)
        self.state_panel_layout.addWidget(self.camera_connection_led, 0, 9, 1, 1)
        self.state_panel_layout.addWidget(self.trig_connection_label, 1, 0, 1, 5)
        self.state_panel_layout.addWidget(self.trig_connection_state_label, 1, 5, 1, 4)
        self.state_panel_layout.addWidget(self.trig_connection_led, 1, 9, 1, 1)

        self.state_panel.setLayout(self.state_panel_layout)

    # file system, folder
    def _file_system_viewer(self):
        '''
        Pannel for directory tree 
        '''
        self.file_panel = QGroupBox('Files')
        self.file_panel.setFont(QFont('Arial', 10))
        self.file_panel_layout = QGridLayout()

        # define file system viewer
        self.tree_view = FileTreeView()

        # set widgets for filesystem
        self.file_browser_btn = QPushButton('File browser')
        self.cd_parent_btn = QPushButton('Parent directory')
        self.rename_btn = QPushButton('Rename')
        self.del_btn = QPushButton('Delete')
        self.mkdir_btn = QPushButton('New folder')
        self.path_label = QLabel('Path')
        self.current_path_label = QLabel(f'{self.tree_view.current_dir}')
        self.current_path_label.setWordWrap(True)
        self.Exp_name_label = QLabel('Exp. name')
        self.experiment_name_edit = QLineEdit('')

        self.file_panel_layout.addWidget(self.tree_view, 0, 0, 9, -1)
        self.file_panel_layout.addWidget(self.file_browser_btn, 10, 0, 1, 2)
        self.file_panel_layout.addWidget(self.cd_parent_btn, 10, 2, 1, 2)

        self.file_panel_layout.addWidget(self.rename_btn, 11, 0, 1, 2)
        self.file_panel_layout.addWidget(self.mkdir_btn, 11, 2, 1, 2)
        self.file_panel_layout.addWidget(self.del_btn, 11, 4, 1, 2)

        self.file_panel_layout.addWidget(self.path_label, 12, 0, 1, 1)
        self.file_panel_layout.addWidget(self.current_path_label, 12, 1, 1, -1)
        self.file_panel_layout.addWidget(self.Exp_name_label, 13, 0, 1, 1)
        self.file_panel_layout.addWidget(self.experiment_name_edit, 13, 1, 1, -1)
        
        self.rename_btn.clicked.connect(self.tree_view._rename)
        self.del_btn.clicked.connect(self.tree_view._delete)
        self.cd_parent_btn.clicked.connect(self.tree_view._mvoe_parent_dir)
        self.file_browser_btn.clicked.connect(self.tree_view._file_browser)
        self.mkdir_btn.clicked.connect(self.tree_view._mkdir)
        self.experiment_name_edit.textChanged.connect(self._set_exp_name)

        self.file_panel.setLayout(self.file_panel_layout)

    # imaging control panel
    def _imaging_control_panel(self):
        '''
        Panel for imaging control 
        ''' 
        self.imaging_panel = QGroupBox('Imaging control')
        self.imaging_panel.setFont(QFont('Arial', 10))
        self.imaging_panel_layout = QGridLayout()

        # generate button and label for imaging
        self.live_btn = QPushButton('Live')
        self.stop_btn = QPushButton('Stop')
        self.set_trigger_btn = QPushButton('Set trigger')
        self.duration_label = QLabel('Duration (s)')
        self.acq_time_sec = QLineEdit()
        self.num_frames_label = QLabel(f'{0} frames')
        self.acq_time_min_label = QLabel(f'{0} min {0} sec')

        # align button and labels
        self.imaging_panel_layout.addWidget(self.live_btn, 0, 0, 1, 3)
        self.imaging_panel_layout.addWidget(self.stop_btn, 0, 3, 1, 3)
        self.imaging_panel_layout.addWidget(self.set_trigger_btn, 0, 6, 1, 3)
        self.imaging_panel_layout.addWidget(self.duration_label, 2, 0, 1, 1)
        self.imaging_panel_layout.addWidget(self.acq_time_sec, 2, 1, 1, -1)

        self.imaging_panel_layout.addWidget(self.num_frames_label, 4, 0, 1, -1)
        self.num_frames_label.setAlignment(Qt.AlignRight)
        self.imaging_panel_layout.addWidget(self.acq_time_min_label, 5, 0, 1, -1)
        self.acq_time_min_label.setAlignment(Qt.AlignRight)

        self.imaging_panel.setLayout(self.imaging_panel_layout)

        # connect live, stop button with camera
        self.live_btn.clicked.connect(self._resume_live_imaging)
        self.stop_btn.clicked.connect(self._stop_live_imaging)
        self.acq_time_sec.setValidator(QDoubleValidator(0, 100, 3, self)) 
        self.acq_time_sec.textChanged.connect(self._set_imaging_duration) # self.acq_time_sec.returnPressed.connect()
        self.set_trigger_btn.clicked.connect(self._set_recording)
        
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

    def _divide_control_panel(self):
        '''
        Assign panel ratio
        '''
        self.control_panel_layout.addWidget(self.state_panel, 1)
        self.control_panel_layout.addWidget(self.file_panel, 6)
        self.control_panel_layout.addWidget(self.imaging_panel, 1)

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
        
        self.splt2.setSizes([150, 100])
        self.splt1.setSizes([100, 100])
        self.main_layout.addWidget(self.splt2)
    
    '''
    signal slots
    '''
    @pyqtSlot()
    def _set_exp_name(self):
        self.current_path_label.setText(f'{self.tree_view.current_dir}')

    @pyqtSlot(QImage)
    def display_image(self, qimage):
        self.live_pixmap = QPixmap.fromImage(qimage)
        self.live_pixmap.scaled(720, 470, Qt.KeepAspectRatioByExpanding)
        self.display_label.setPixmap(self.live_pixmap)
    
    @pyqtSlot()
    def _resume_live_imaging(self):
        if not self.ic.IC_IsDevValid(self.camera):
            self._init_camera()
        self.live = LiveDisplay(self)
        self.live.Pixmap_display.connect(self.display_image)  
        self.live.start()

    @pyqtSlot()
    def _stop_live_imaging(self):
        self.live.pause()

    @pyqtSlot()
    def _set_imaging_duration(self):
        duration = self.acq_time_sec.text()
        try:
            self.duration = float(duration) # sec
            self.frames = int(np.floor(self.duration * self.frame_rate)) # frames
            self.num_frames_label.setText(f'{self.frames:>20d} frames')
            self.acq_time_min_label.setText(f'{self.duration//60:>20.0f} min {self.duration%60:>02.0f} sec')
        except:
            self.num_frames_label.setText(f'0 frames')
            self.acq_time_min_label.setText(f'{0:>20.0f} min {0:>02.0f} sec')

    @pyqtSlot()
    def _set_recording(self):
        # camera and trigger device connection check
        if not self.ic.IC_IsDevValid(self.camera):
            QMessageBox.about(self, 'Connection Error!', 'Connect camera')

        elif self.trig is None:
            QMessageBox.about(self, 'Connection Error!', 'Connect trigger device')
        
        elif (not self.ic.IC_IsDevValid(self.camera)) and (self.trig is None):
            QMessageBox.about(self, 'Connection Error!', 'Connect camera and trigger device')

        # ready to receive TTL signal after all devices are connected
        else:
            # check the No. of frames (or recording duration) to record
            if self.frames <= 0:
                QMessageBox.about(self, 'Setting Error!', 'Enter the more than 1 frames')
                self.acq_time_sec.text()
            # check save path and dirctory name
            # ready to get TTL trigger
            # imaging
            # save images
            pass

    @pyqtSlot(bool)
    def _connection_state_view(self, refresh):
        if refresh:
            # Check camera connection state
            if self.ic.IC_IsDevValid(self.camera):
                self.camera_connection_state_label.setText('Connected')
                self.camera_connection_led.setStyleSheet("QLabel {background-color : green; border-color : black; \
                                                            border-style : default; border-width : 0px; \
                                                            border-radius : 19px; min-height: 3px; min-width: 5px}")
            else:
                self.camera_connection_state_label.setText('Disconnected')
                self.camera_connection_led.setStyleSheet("QLabel {background-color : red; border-color : black; \
                                                            border-style : default; border-width : 0px; \
                                                            border-radius : 19px; min-height: 3px; min-width: 5px}")

            try:
                self.trig = InstantDiCtrl(self.dev_description)
                self.trig_connection_state_label.setText('Connected')
                self.trig_connection_led.setStyleSheet("QLabel {background-color : green; border-color : black; \
                                                        border-style : default; border-width : 0px; \
                                                        border-radius : 19px; min-height: 3px; min-width: 5px}")
            except:
                self.trig = None
                self.trig_connection_state_label.setText('Disconnected')
                self.trig_connection_led.setStyleSheet("QLabel {background-color : red; border-color : black; \
                                                        border-style : default; border-width : 0px; \
                                                        border-radius : 19px; min-height: 3px; min-width: 5px}")

if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())
