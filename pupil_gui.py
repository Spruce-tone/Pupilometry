import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, \
                            qApp, QDesktopWidget, QMessageBox, QWidget, QTabWidget
from PyQt5.QtCore import pyqtSlot
from lib.MainWidget import MainWidget

class pupil(QMainWindow):    
    def __init__(self, height=500, width=500):
        super().__init__()
        self.H = 1400
        self.W = 1600
        
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
        self.resize(self.W, self.H)

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
        self.dlcMenu = self.fileMenu.addMenu('&DeepLabCut')

        # select device menu
        selectDeviceAction = QAction('Select Device', self)
        selectDeviceAction.triggered.connect(self._selectdevice)
        self.fileMenu.addAction(selectDeviceAction)

        # Open deeplabcut for training
        launchDeepLabCut = QAction('Launch', self)
        launchDeepLabCut.triggered.connect(self._launchDeepLabcCt)
        self.dlcMenu.addAction(launchDeepLabCut)

        # select models for dynamic pupil size measurments
        selectDLCModelAction = QAction('Select DeepLapCut model', self)
        selectDLCModelAction.triggered.connect(self._selectDLCModel)
        self.dlcMenu.addAction(selectDLCModelAction)

        # extract pupil size from image sequences
        extractPupilsizeAction = QAction('Extract Pupil size', self)
        extractPupilsizeAction.triggered.connect(self._extractPupilSize)
        self.dlcMenu.addAction(extractPupilsizeAction)

        # Exit menue
        exitAction = QAction('Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self._exitaction)
        self.fileMenu.addAction(exitAction)


    @pyqtSlot()
    def _selectdevice(self):
        self.ic.IC_StopLive(self.main_widget.camera)
        self.ic.IC_ShowDeviceSelectionDialog(None)

        if self.ic.IC_IsDevValid(self.main_widget.camera):
            self.ic.IC_StartLive(self.main_widget.camera, 0)
            self.ic.IC_SaveDeviceStateToFile(self.camera, b'device.xml')
    
    @pyqtSlot()
    def _launchDeepLabcCt(self):
        self.main_widget._launch_deeplabcut()

    @pyqtSlot()
    def _selectDLCModel(self):
        self.main_widget._dlc_model()
    
    @pyqtSlot()
    def _extractPupilSize(self):
        self.main_widget._extract_pupil_size()
    @pyqtSlot()
    def _exitaction(self):
        if self.ic.IC_IsDevValid(self.main_widget.camera):
            self.ic.IC_StopLive(self.main_widget.camera)
            self.ic.IC_ReleaseGrabber(self.main_widget.camera)
        self.main_widget.refresh_dev.stop()
        self.main_widget.get_img.stop()
        qApp.quit()

if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())
