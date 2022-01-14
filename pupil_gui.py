import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, qApp, QDesktopWidget
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





 

if __name__=='__main__':
    app = QApplication(sys.argv)
    ex = pupil()
    sys.exit(app.exec_())
