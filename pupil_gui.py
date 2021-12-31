import sys, os, shutil, time, ctypes, re
from typing import Union, List, Tuple, Set, Dict
from PyQt5.QtWidgets import QApplication, QBoxLayout, QDialog, QFileDialog, QFileSystemModel, \
                            QInputDialog, QSplitter, QTreeView, QTreeWidget, QWidget, QPushButton, \
                            QToolTip, QMainWindow, QAction, qApp, \
                            QDesktopWidget, QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout, QLabel, QGroupBox, QTextEdit, \
                            QLineEdit, QAbstractItemView, QTreeWidgetItem, \
                            QMessageBox, QDoubleSpinBox
from PyQt5.QtCore import QCoreApplication, QDate, QEventLoop, QItemSelectionModel, Qt, \
                        QTime, pyqtSignal, QThread, pyqtSlot, QItemSelection, \
                        QDir
from PyQt5.QtGui import QFont, QPixmap, QImage, QDoubleValidator, QKeyEvent, QIntValidator
from lib import tisgrabber as tis
import numpy as np
from skimage import io
from datetime import datetime


sys.path.append('./lib')
from lib.SignalConnection import LiveDisplay, RefreshDevState, TriggeredRecording
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
    Nonce = 0
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
    def _mk_new_dir(self):
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

    def get_parent_dir(self) -> str:
        # when one file is selected
        if len(self.index)==1:
            # if selected file is directory, the directory is set as parent
            if self.model.isDir(self.index[0]):
                parent = self.index[0]
            # if selected file is not directory, set current directory as parent
            else:
                parent = self.model.index(self.current_dir)
        # if more than one or no file is selected 
        else:
            # set current directory (working directory) as parent  
            parent = self.model.index(self.current_dir)

        return parent

    def mk_exp_dir(self, parent : str, exp_name: str):
        # analyze name for duplication check
        dir_filter = re.compile('(?P<nonce>_\d{4})')
        filtered_name = dir_filter.search(exp_name)

        # add nonce to file name if no nonce
        if filtered_name==None:
            # if there is same directory name, add nonce to exp name
            exp_name = f'{exp_name}_{self.Nonce:04d}'

        # duplicate check
        while True:
            duplicate_check = True
            for file in os.listdir(self.model.filePath(parent)):
                if file==exp_name: # duplicate dir check
                    
                    exp_name = dir_filter.sub(f'_{self.Nonce:04d}', exp_name)
                    self.increase_nonce() # update new nonce    

                    duplicate_check = False
            
            # if there is no duplicate dir, break the while loop
            if duplicate_check:
                break
        
        self.exp_name = exp_name
        self.increase_nonce() # update new nonce           
        self.model.mkdir(parent, self.exp_name)

    def increase_nonce(self):
        self.Nonce += 1

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
        self.max_fps = float(29.970000)
        self.min_fps = float(0.000001)
        self.frame_rate = 2
        self.frames = 550
        self.img_size_GB = sys.getsizeof(np.zeros(shape=(1, 480, 720, 3))) / 2**30 # memory size of single frame image
    
    def _init_trigger(self):
        '''
        trigger device description, adventech usb-4751L
        '''
        self.dev_description = "USB-4751L,BID#0"
        self.startPort = 2
        self.portCount = 1

        try:
            self.trig = InstantDiCtrl(self.dev_description)
        except:
            self.trig = None

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
        self.mkdir_btn.clicked.connect(self.tree_view._mk_new_dir)
        self.experiment_name_edit.textChanged.connect(self._set_exp_name)
        self.experiment_name_edit.setText('Exp_0000')

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
        self.cancel_trigger_btn = QPushButton('Trigger cancel ')
        self.cancel_trigger_btn.setEnabled(False)
        self.frame_rate_label = QLabel('Frame rate (Hz)')
        self.set_frame_rate = QLineEdit()
        self.frames_label = QLabel('Frames')
        self.acq_frames = QLineEdit()
        self.acq_time_min_label = QLabel(f'{0} min {0} sec {0} GB')

        # align button and labels
        self.imaging_panel_layout.addWidget(self.live_btn, 0, 0, 1, 3)
        self.imaging_panel_layout.addWidget(self.stop_btn, 0, 3, 1, 3)
        self.imaging_panel_layout.addWidget(self.set_trigger_btn, 0, 6, 1, 3)
        self.imaging_panel_layout.addWidget(self.cancel_trigger_btn, 0, 9, 1, 3)
        self.imaging_panel_layout.addWidget(self.frame_rate_label, 1, 0, 1, 3)
        self.imaging_panel_layout.addWidget(self.set_frame_rate, 1, 3, 1, -1)
        self.imaging_panel_layout.addWidget(self.frames_label, 2, 0, 1, 3)
        self.imaging_panel_layout.addWidget(self.acq_frames, 2, 3, 1, -1)
        self.imaging_panel_layout.addWidget(self.acq_time_min_label, 3, 0, 1, -1)
        self.acq_time_min_label.setAlignment(Qt.AlignRight)
        

        self.imaging_panel.setLayout(self.imaging_panel_layout)

        # connect live, stop button with camera
        self.live_btn.clicked.connect(self._resume_live_imaging)
        self.stop_btn.clicked.connect(self._stop_live_imaging)

        self.set_frame_rate.setValidator(QDoubleValidator()) # set frame rate format : double
        self.set_frame_rate.editingFinished.connect(self._set_frame_rate)
        # set default frame rate
        if self.set_frame_rate.text()=='':
            self.set_frame_rate.setText(f'{self.frame_rate:.6f}')
            self.set_frame_rate.completer()

        self.acq_frames.setValidator(QIntValidator(0, 10000000, self)) # set available No. of frame range for recording
        self.acq_frames.textChanged.connect(self._set_imaging_frames)
        # set default frame numbers
        if self.acq_frames.text()=='':
            self.acq_frames.setText(f'{self.frames}')
            self.acq_frames.completer()
        self.set_trigger_btn.clicked.connect(self._set_recording)
        self.cancel_trigger_btn.clicked.connect(self._stop_trigger)
        
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
    
    def _set_enable_inputs(self, enable : bool=True):
        # button and line edit on file system panel
        self.tree_view.setEnabled(enable)
        self.file_browser_btn.setEnabled(enable)
        self.cd_parent_btn.setEnabled(enable)
        self.rename_btn.setEnabled(enable)
        self.del_btn.setEnabled(enable)
        self.mkdir_btn.setEnabled(enable)
        self.experiment_name_edit.setEnabled(enable)

        # button and line edit on imaging control panel
        self.live_btn.setEnabled(enable)
        self.stop_btn.setEnabled(enable)
        self.acq_frames.setEnabled(enable)
        self.set_frame_rate.setEnabled(enable)
        self.set_trigger_btn.setEnabled(enable)
        self.cancel_trigger_btn.setEnabled(not enable)

    '''
    signal slots
    '''
    @pyqtSlot()
    def _set_exp_name(self):
        self.current_path_label.setText(f'{self.tree_view.current_dir}')

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
    def _set_imaging_frames(self):
        if (self.set_frame_rate.text()=='') and (self.acq_frames.text()!=''):
            self.acq_frames.setText('')
            QMessageBox.about(self, 'Notice!', f'You have to set the frame rate first')
        
        else:      
            frames = self.acq_frames.text()
            try:
                self.frames = int(frames)
                self.memory = self.frames * self.img_size_GB
                self.duration = self.frames / self.frame_rate
                self.acq_time_min_label.setText(f'{(self.duration//60)//60:>3.0f} hours {(self.duration//60)%60:>02.0f} min {self.duration%60:>02.0f} sec {self.memory:>03.3f} GB')
            except:
                self.acq_time_min_label.setText(f'{0:>3.0f} hours {0:>2.0f} min {0:>02.0f} sec {0:>04.0f} GB')

    @pyqtSlot()
    def _set_frame_rate(self):
        # get frame rate from line edit input
        frame_rate = float(self.set_frame_rate.text())

        # restrict the frame rate betweent 0.000001 and 29.97 Hz
        if frame_rate > self.max_fps:
            QMessageBox.about(self, 'Notice!', f'The maximum frame rate is {self.max_fps:.2f} Hz')
            frame_rate = self.max_fps
        elif frame_rate < self.min_fps:
            frame_rate = self.min_fps

        # set frame rate and terminate
        self.frame_rate = frame_rate
        self.set_frame_rate.setText(f'{self.frame_rate:.6f}')
        self.set_frame_rate.completer()

    @pyqtSlot()
    def _stop_trigger(self):
        self.triggered_recording.stop()
        self._set_enable_inputs(True)

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
            # check whether the trigger device and TTL source are connected by BNC cable
            _, data = self.trig.readAny(self.startPort, self.portCount)
            if data==[255]:
                QMessageBox.about(self, 'Connection Error!', 'Connect the trigger device to TTL source using BNC cable')
                return

            # check the No. of frames (or recording duration) to record
            if (self.acq_frames.text()=='') or (self.frames <= 0):
                QMessageBox.about(self, 'Setting Error!', 'Enter the more than 1 frames')
                return
            
            # check parent directory to save recording
            self.parent_idx = self.tree_view.get_parent_dir()

            # if the parent dir is determined, refresh save path
            self.current_path_label.setText(self.tree_view.model.filePath(self.parent_idx))

            # if no input at experiment name, set default name as 'Exp'
            if self.experiment_name_edit.text()=='':
                save_dir_name = 'Exp'
                self.experiment_name_edit.setText(save_dir_name)
            else:
                save_dir_name = self.experiment_name_edit.text()

            # make dir to save images
            self.tree_view.mk_exp_dir(self.parent_idx, save_dir_name)            

            # if frame rate is larger than 15 Hz
            # user have to select whether start recording with or without  monitoring
            # if user want to monitor, the frame rate is set to 15 Hz 
            if self.frame_rate > 15:
                reply = QMessageBox.question(self, 'Notice!', 
                                            'You can''t monitor the recording if the frame rate is larger than 15 Hz. \
                                            Do you want to record without monitoring?',
                                            QMessageBox.Yes | QMessageBox.No)
                
                # if yes, record movie without monitoring
                if reply==QMessageBox.Yes:
                    self.live.stop()
                else:
                    self.frame_rate = 15
                    self.set_frame_rate.setText(f'{self.frame_rate:.6f}')
                    self.set_frame_rate.completer()
            
            # disable any button and input during trigger
            self._set_enable_inputs(False)
            
            # ready TTL trigger
            # if the device receive TTL signal, start recording 
            self.triggered_recording = TriggeredRecording(self)
            self.triggered_recording.start()
            self.triggered_recording.recording_termination.connect(self._stop_trigger)
            self.triggered_recording.save_img.connect(self._save_img)

    @pyqtSlot(int, np.ndarray)
    def _save_img(self, idx : int, img : np.ndarray):
        print(idx)
        save_dir = f'{self.tree_view.model.filePath(self.parent_idx)}/{self.tree_view.exp_name}'
        current_time = datetime.now()
        current_time = current_time.strftime('%Y-%m-%d_%Hhr-%Mmin-%Ssec')
        img_name = f'{idx:05d}_{current_time}.tif'

        file_name = os.path.join(save_dir, img_name)
        print(file_name)
        print(img.shape)
        print(save_dir)
        print(current_time)
        print(img_name, '\n')
        io.imsave(file_name, img)


        

    '''
    functions (slots) resppond to Thread
    '''
    @pyqtSlot(QImage)
    def display_image(self, qimage):
        self.live_pixmap = QPixmap.fromImage(qimage)
        self.live_pixmap.scaled(720, 470, Qt.KeepAspectRatioByExpanding)
        self.display_label.setPixmap(self.live_pixmap)

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
