import sys, os, shutil, ctypes, re, csv
from PyQt5.QtWidgets import QFileDialog, QFileSystemModel, \
                            QInputDialog, QSplitter, QTreeView, QWidget, QPushButton, \
                            QHBoxLayout, QVBoxLayout, \
                            QFrame, QGridLayout, QLabel, QGroupBox, \
                            QLineEdit, QAbstractItemView, QMessageBox, \
                            QProgressBar, QCheckBox, QListView, QDialog
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QImage, QDoubleValidator, QKeyEvent, \
                        QIntValidator, QPainter, QPen
# from cv2 import FlannBasedMatcher
from lib import tisgrabber as tis
import numpy as np
from skimage import io
from datetime import datetime
import cv2
from dlclive import DLCLive, Processor
from typing import Dict, List, Union
import deeplabcut

from lib.utils import find_circle

sys.path.append('./lib')
if (sys.version_info.minor <= 7) and (sys.version_info.major==3): # add .dll search path for python 3.7 and older
    os.environ['PATH'] = os.path.abspath('./lib') + os.pathsep + os.environ['PATH']

from lib.SignalConnection import GetCamImage, RefreshDevState
from lib.Automation.BDaq.InstantDiCtrl import InstantDiCtrl

class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # initialize and connect camera
        self._init_camera()

        # initialize and connect trigger device
        self._init_trigger()

        # initialize dynamic plot state   
        self._init_dynamic_plot_state()

        # Define main layout
        self.main_layout = QHBoxLayout()
        
        # Generate and assign the frame layout
        self._generate_frames()
        self._main_division()

        # set main layout
        self.setLayout(self.main_layout)

        # movie display
        self._add_movie_widget()

        # live graph display
        self._add_graph_widget()
        
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
        # self.ic = ctypes.cdll.LoadLibrary('./lib/tisgrabber_x64.dll')
        self.ic = ctypes.CDLL('./lib/tisgrabber_x64.dll')
        tis.declareFunctions(self.ic)
        self.ic.IC_InitLibrary(0)

        # connect camera
        self.camera = tis.openDevice(self.ic)
        self.max_fps = float(29.970000)
        self.min_fps = float(0.000001)
        self.frame_rate = 2
        self.frames = 550
        self.img_width = 720
        self.img_height = 480
        self.img_channels = 3
        # size of single frame image in GB
        # 24 bit, 480 x 720 pixels RGB image
        self.img_size_GB = self.img_width * self.img_height * 24 / 8 / 2**30
        self.recording_type = 'LiveDisplay'
        self.img_formats = ('.tif', '.jpg', '.png', '.jpeg') 
    
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

    def _init_dynamic_plot_state(self):
        self.dynamic_plot = False
        self.fit_threshold = 0.9

    def _dlc_model(self):
        reply = QMessageBox.question(self, 'Load DeepLabCut model', 
                                            'Do you want to load models to extract pupil size?',
                                            QMessageBox.Yes | QMessageBox.No)
                
        # if yes, record movie without monitoring
        if reply==QMessageBox.Yes:
            QMessageBox.about(self, 'Select DeepLabCut model', \
                            f'Select DeepLabCut model path where containing "pose_cfg.yaml" file')
            try:
                dlc_proc = Processor()
                self.dlc_model_path = QFileDialog.getExistingDirectory()
                self.dlclive = DLCLive(self.dlc_model_path, processor=dlc_proc)
                self.dlclive.init_inference()
                self.dynamic_plot = True
                self._dynamicplot_set(self.dynamic_plot)
                self._define_data_parser()
            except:
                QMessageBox.about(self, 'Failed to select DeepLabCut model', \
                            f'Please check the model path and "pose_cfg.yaml" file')

    def _launch_deeplabcut(self):
        deeplabcut.launch_dlc()

    def _extract_pupil_size(self):
        '''
        Extract pupil size from saved images
        '''
        if not self.dynamic_plot:
            self._dlc_model()
        QMessageBox.about(self, 'Select directories ', \
                            f'Select directories containing pupil images')

        dir_paths = self._get_dir_paths()
        
        if len(dir_paths) > 0: # one or more directories are selected, execute the loop
            for path in dir_paths:
                img_names = [names for names in os.listdir(path) if names.endswith(self.img_formats)]
                img_names = sorted(img_names, key=lambda x: int(x[:6]))

                if len(img_names) > 0: # if no images, run the next loop
                    pupil_data = []

                    for idx, img_name in enumerate(img_names):
                        img_data = {}
                        img = io.imread(os.path.join(path, img_name))
                        
                        meta = self.parser.search(img_name)
                        if meta==None:
                            img_index = idx
                        else:
                            img_index = int(meta.group('index'))

                        time_stamp = self._parse_timestamp(meta)
                        
                        self._metadatar_parsing(img_data, img_index, img_name, time_stamp) # save metadata
                        dlc_output = self.dlclive.get_pose(img) # key points coordinate
                        self._pupil_parsing(img_data, dlc_output)
                        
                        if idx==0:
                            self.keys = img_data.keys()
                        pupil_data.append(img_data)
                    
                    try:
                        with open(f'{path}.csv', 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=self.keys)
                            writer.writeheader()
                            for row in pupil_data:
                                writer.writerow(row)
                    except:
                        QMessageBox.about(self, 'Save error!', \
                            f'Save error for "{os.path.basename(path)}" directory')


    def _get_dir_paths(self) -> List[str]:
        '''
        get directories' name from file manager

        ----------
        Return
        -----------
        dir_paths : list
            path of directories that contain saved pupil images 
        '''
        dialog = QFileDialog(self)
        dialog.setWindowTitle('Choose Directories')
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setDirectory(os.getcwd())
        for view in dialog.findChildren((QListView, QTreeView)):
            if isinstance(view.model(), QFileSystemModel):
                view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        if dialog.exec_() == QDialog.Accepted:
            dir_paths = dialog.selectedFiles()
            return dir_paths
        else:
            return []

    def _define_data_parser(self):
        self.metadata_keys = ['index', 'img_name', 'time_stamp', 'time']
        self.dlc_keys = ['num_points', 'xc', 'yc', 'radius', 'probability']
        self.parser = re.compile('(?P<index>\d{6})_(?P<time_stamp>\d{4}-\d{2}-\d{2}_\d{2}hr-\d{2}min-\d{2}.\d{6}sec).tif')

    def _parse_timestamp(self, meta: Union[re.Match, None]) -> Union[None, datetime]:
        '''
        timestamp parsing from image name
        ----------
        Input Args
        -----------
        meta : re.Match or NoneType
            regular expression parser for data extraction
        '''
        if meta==None:
            return None
        else:
            time_stamp = datetime.strptime(meta.group('time_stamp'), '%Y-%m-%d_%Hhr-%Mmin-%S.%fsec')
            return time_stamp

    def _metadatar_parsing(self, img_data: Dict, img_index: int, img_name: str, time_stamp: Union[datetime, None]):
        '''
        Metadata parsing from image name
        ----------
        Input Args
        -----------
        img_data : dict
            dictionary to store metadate
        img_index : int
            index based on image name
        img_name : str
            image name
        time_stamp : None or datetime.datetime
            time stamp when image was acquired
        '''
        # if no metadata, assign index depend on image name 
        if time_stamp==None:
            img_data['index'] = img_index
            img_data['img_name'] = img_name
            img_data['time_stamp'], img_data['time (sec)'] = '', ''
        else:
            if img_index==0: # if first image, save time stamp to get relative imaging time
                self.first_time_stamp = time_stamp

            img_data['index'] = img_index
            img_data['img_name'] = img_name
            img_data['time_stamp'] = datetime.strftime(time_stamp, '%Y-%m-%d_%H:%M:%S.%f')
            img_data['time (sec)'] = (time_stamp - self.first_time_stamp).total_seconds() # relative imaging time

    def _pupil_parsing(self, img_data: Dict, dlc_output: np.ndarray):
        '''
        Pupil data parsing from image
        ----------
        Input Args
        -----------
        img_data : dict
            dictionary to store metadate
        dlc_output : np.ndarray
            key points coordinates and probability
        '''
        center, radius, probability, num_points = find_circle(dlc_output) # dlc outputs
        xc, yc = center # pupil center coordinates

        for dlc_key, dlc_value in zip(self.dlc_keys, [num_points, xc, yc, radius, probability]):
            img_data[dlc_key] = dlc_value # store dlc output
        
        for idx, coords in enumerate(dlc_output): # extract key point coordinates
            x, y, _ = coords
            img_data[f'x{idx}'] = x # x-coordinate of n th key point 
            img_data[f'y{idx}'] = y # y-coordinate of n th key point

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
        self.get_img = GetCamImage(self)
        self.get_img.start()
        self.get_img.Pixmap_display.connect(self.display_image)

        # checkbox to show the fitted circle on pupil
        self.movie_frame.setFont(QFont('Arial', 12))
        self.show_circle = QCheckBox('Show circle')
        self.set_thesh_label = QLabel(f'Set Threshold : {self.fit_threshold:.6f}')
        self.set_fit_threshold = QLineEdit()
        self.live_frame_rate = QLabel(f'Frame rate : {0:2.2f}')

        self.set_fit_threshold.setValidator(QDoubleValidator()) # set frame rate format : double
        self.set_fit_threshold.editingFinished.connect(self._set_fit_threshold)
        # set default frame rate
        if self.set_fit_threshold.text()=='':
            self.set_fit_threshold.setText(f'{self.fit_threshold:.6f}')
            self.set_fit_threshold.completer()
        self._dynamicplot_set(False) # deactivate setting for dynamic plot
        
        # add widget
        self.movie_layout.addWidget(self.show_circle, 1, 1, 1, 1)
        self.movie_layout.addWidget(self.set_thesh_label, 1, 5, 1, 4)
        self.movie_layout.addWidget(self.set_fit_threshold, 1, 9, 1, 2)
        self.movie_layout.addWidget(self.display_label, 2, 1, 10, -1)
        self.movie_layout.addWidget(self.live_frame_rate, 12, 10, -1, 1)
    
    # graph widget
    def _add_graph_widget(self):
        '''
        generate graph widget
        if start the dynamic pupil size measurements, plot the graph  
        '''
        # generate display widget


    def _dynamicplot_set(self, dynamic_plot_state: bool):
        self.show_circle.setEnabled(dynamic_plot_state)
        self.set_thesh_label.setEnabled(dynamic_plot_state)
        self.set_fit_threshold.setEnabled(dynamic_plot_state)


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
        self.experiment_name_edit.setText('Exp')

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
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setEnabled(False)
        self.recording_btn = QPushButton('Recording')
        self.frame_rate_label = QLabel('Frame rate (Hz)')
        self.set_frame_rate = QLineEdit()
        self.frames_label = QLabel('Frames')
        self.acq_frames = QLineEdit()
        self.progress_check = QLabel(f'Progress | {0:06d}/{self.frames:06d}')
        self.acq_time_min_label = QLabel(f'{0} min {0} sec {0} GB')
        self.progress_bar = QProgressBar()
        

        # align button and labels
        self.imaging_panel_layout.addWidget(self.live_btn, 0, 0, 1, 3)
        self.imaging_panel_layout.addWidget(self.stop_btn, 0, 3, 1, 3)
        self.imaging_panel_layout.addWidget(self.recording_btn, 0, 6, 1, 3)
        self.imaging_panel_layout.addWidget(self.set_trigger_btn, 0, 9, 1, 3)
        self.imaging_panel_layout.addWidget(self.cancel_btn, 0, 12, 1, 3)
        

        self.imaging_panel_layout.addWidget(self.frame_rate_label, 1, 0, 1, 6)
        self.imaging_panel_layout.addWidget(self.set_frame_rate, 1, 6, 1, -1)
        self.imaging_panel_layout.addWidget(self.frames_label, 2, 0, 1, 6)
        self.imaging_panel_layout.addWidget(self.acq_frames, 2, 6, 1, -1)
        self.imaging_panel_layout.addWidget(self.progress_check, 3, 0, 1, 6)
        self.imaging_panel_layout.addWidget(self.acq_time_min_label, 3, 3, 1, -1)
        self.acq_time_min_label.setAlignment(Qt.AlignRight)
        self.imaging_panel_layout.addWidget(self.progress_bar, 4, 0, 1, -1)
        

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

        self.acq_frames.setValidator(QIntValidator(0, 1000000, self)) # set available No. of frame range for recording
        self.acq_frames.textChanged.connect(self._set_imaging_frames)
        
        # set default frame numbers
        if self.acq_frames.text()=='':
            self.acq_frames.setText(f'{self.frames}')
            self.acq_frames.completer()

        self.set_trigger_btn.clicked.connect(self._set_recording)
        self.cancel_btn.clicked.connect(self._stop_recording)
        self.recording_btn.clicked.connect(self._start_recording) ### make recording signal ############ in progress
        
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
        self.recording_btn.setEnabled(enable)
        self.set_trigger_btn.setEnabled(enable)
        self.cancel_btn.setEnabled(not enable)

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
            self.get_img = GetCamImage(self)
            self.get_img.Pixmap_display.connect(self.display_image)  
        self.get_img.start()
        self.get_img.resume()

    @pyqtSlot()
    def _stop_live_imaging(self):
        self.get_img.pause()

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
                self.progress_check.setText(f'Progress | {0:06d}/{self.frames:06d}')
                self.progress_bar.setMaximum(self.frames)
                self.progress_bar.setValue(0)
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
    def _set_fit_threshold(self):
        # get frame rate from line edit input
        fit_threshold = float(self.set_fit_threshold.text())
        
        # restrict pupil fitting threshold betweent 0 and 1
        if fit_threshold < 0:
            fit_threshold = 0
        elif fit_threshold > 1:
            fit_threshold = 1

        # set frame rate and terminate
        self.fit_threshold = fit_threshold
        self.set_fit_threshold.setText(f'{self.fit_threshold:.6f}')
        self.set_fit_threshold.completer()
        self.set_thesh_label.setText(f'Set Threshold : {self.fit_threshold:.6f}')

    @pyqtSlot()
    def _stop_recording(self):
        self.get_img.stop()
        self.recording_type='LiveDisplay'
        self._set_enable_inputs(True)
        self._dynamicplot_set(self.dynamic_plot)
        self.video.release()

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
            
            # reset the progress
            self.progress_bar.setValue(0)
            self.progress_check.setText(f'Progress | {0:06d}/{self.frames:06d}')

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
                    self.get_img.stop()
                else:
                    self.frame_rate = 15
                    self.set_frame_rate.setText(f'{self.frame_rate:.6f}')
                    self.set_frame_rate.completer()
            
            # disable any button and input during trigger and dynamic plot setting
            self._set_enable_inputs(False)
            self._dynamicplot_set(False)
            
            # ready TTL trigger
            # if the device receive TTL signal, start recording 
            self.recording_type = 'Triggered'
            self.get_img.set_recording_mode()
            self.get_img.recording_termination.connect(self._stop_recording)
            self.get_img.save_img.connect(self._save_img)
            self.get_img.Pixmap_display.connect(self.display_image)

            # generate video
            video_name = f'{self.tree_view.model.filePath(self.parent_idx)}/{self.tree_view.exp_name}.avi'
            fourcc = cv2.VideoWriter_fourcc(*'MJPG') # set codec  
            self.video = cv2.VideoWriter(video_name, fourcc, self.frame_rate, (self.img_width, self.img_height))

    @pyqtSlot()
    def _start_recording(self):
        # camera and trigger device connection check
        if not self.ic.IC_IsDevValid(self.camera):
            QMessageBox.about(self, 'Connection Error!', 'Connect camera')

        # ready to start recording after camera devices are connected
        else:
            # check the No. of frames (or recording duration) to record
            if (self.acq_frames.text()=='') or (self.frames <= 0):
                QMessageBox.about(self, 'Setting Error!', 'Enter the more than 1 frames')
                return
            
            # reset the progress
            self.progress_bar.setValue(0)
            self.progress_check.setText(f'Progress | {0:06d}/{self.frames:06d}')

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
                    self.get_img.stop()
                else:
                    self.frame_rate = 15
                    self.set_frame_rate.setText(f'{self.frame_rate:.6f}')
                    self.set_frame_rate.completer()
            
            # disable any button and input during trigger and dynamics plot setting
            self._set_enable_inputs(False)
            self._dynamicplot_set(False)
            
            # start recording 
            self.recording_type = 'Manual'
            self.get_img.set_recording_mode()
            self.get_img.recording_termination.connect(self._stop_recording)
            self.get_img.save_img.connect(self._save_img)
            self.get_img.Pixmap_display.connect(self.display_image)

            # generate video
            video_name = f'{self.tree_view.model.filePath(self.parent_idx)}/{self.tree_view.exp_name}.avi'
            fourcc = cv2.VideoWriter_fourcc(*'MJPG') # set codec  
            self.video = cv2.VideoWriter(video_name, fourcc, self.frame_rate, (self.img_width, self.img_height))


    @pyqtSlot(dict)
    def _save_img(self, live_signal: Dict):
        '''
        live_signal:
            dictionary contain image and metadata
        '''
        idx = live_signal.get('index')
        img = live_signal.get('image')
        current_time = live_signal.get('time_stamp').strftime('%Y-%m-%d_%Hhr-%Mmin-%S.%fsec')
        time_stamp = live_signal.get('time_stamp')
        dlc_output = live_signal.get('dlc_output')

        # set save path and image name
        save_dir = f'{self.tree_view.model.filePath(self.parent_idx)}/{self.tree_view.exp_name}'        
        img_name = f'{idx:06d}_{current_time}.tif'

        # update recording progress
        self.progress_check.setText(f'Progress | {idx+1:06d}/{self.frames:06d}')
        self.progress_bar.setValue(idx+1)

        # save image
        file_name = os.path.join(save_dir, img_name)
        io.imsave(file_name, img)

        # wirte video
        self.video.write(img)
        if idx==(self.frames - 1):
            self.video.release()

            # reset progress monitor
            self.progress_check.setText(f'Progress | {0:06d}/{self.frames:06d}')

        
        # save data (pupil size and metadata)
        if self.show_circle.isChecked() and self.dynamic_plot:
            live_img_data = {}
            self._metadatar_parsing(live_img_data, idx, img_name, time_stamp)
            self._pupil_parsing(live_img_data, dlc_output)

            if idx==0:
                self.keys = live_img_data.keys()
            
            try:
                if not os.path.exists(f'{save_dir}.csv'):
                    with open(f'{save_dir}.csv', 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=self.keys)
                        writer.writeheader()
                        writer.writerow(live_img_data)
                else:
                    with open(f'{save_dir}.csv', 'a', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=self.keys)
                        writer.writerow(live_img_data)

            except:
                QMessageBox.about(self, 'Save error!', \
                    f'Save error for "{os.path.basename(file_name)}" directory')


    '''
    functions (slots) resppond to Thread
    '''
    @pyqtSlot(dict)
    def display_image(self, live_signal: Dict):
        '''
        live_signal:
            dictionary contain image and metadata
        '''
        center, radius, img, fps, probability = (live_signal.get(key) for key in ['center', 'radius', 'qimage', 'frame_rate', 'probability']) 
        
        self.live_pixmap = QPixmap.fromImage(img)
        self.live_pixmap.scaled(self.img_width, self.img_height, Qt.KeepAspectRatioByExpanding)
        self.display_label.setPixmap(self.live_pixmap)
        
        if self.show_circle.isChecked() and (probability >= self.fit_threshold):
            painter = QPainter(self.display_label.pixmap())
            painter.setPen(QPen(Qt.red, 1))
            painter.drawEllipse(center[0] - radius, center[1] - radius, radius*2, radius*2)

        self.live_frame_rate.setText(f'Frame rate : {fps:2.2f}')

    @pyqtSlot(bool)
    def _connection_state_view(self, refresh: bool):
        if refresh:
            # Check camera connection state
            camera = self.ic.IC_LoadDeviceStateFromFile(None, b'device.xml')
            if self.ic.IC_IsDevValid(camera):
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
                
                if self.trig.device.location!=b'':
                    self.trig_connection_state_label.setText('Connected')
                    self.trig_connection_led.setStyleSheet("QLabel {background-color : green; border-color : black; \
                                                            border-style : default; border-width : 0px; \
                                                            border-radius : 19px; min-height: 3px; min-width: 5px}")
                else:
                    self.trig = None
                    self.trig_connection_state_label.setText('Disconnected')
                    self.trig_connection_led.setStyleSheet("QLabel {background-color : red; border-color : black; \
                                                            border-style : default; border-width : 0px; \
                                                            border-radius : 19px; min-height: 3px; min-width: 5px}")

            except:
                self.trig = None
                self.trig_connection_state_label.setText('Disconnected')
                self.trig_connection_led.setStyleSheet("QLabel {background-color : red; border-color : black; \
                                                        border-style : default; border-width : 0px; \
                                                        border-radius : 19px; min-height: 3px; min-width: 5px}")

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
        self.current_dir = QFileDialog.getExistingDirectory(self)
        if self.current_dir != '':
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