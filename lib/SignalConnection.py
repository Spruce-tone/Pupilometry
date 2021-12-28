from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes
import time

from lib.Automation.BDaq.InstantDiCtrl import InstantDiCtrl


class LiveDisplay(QThread):
    Pixmap_display = pyqtSignal(QImage)
    
    def __init__(self, parent):
        super().__init__(parent)
        self.camera = parent.camera
        self.ic = parent.ic

        self.Width = ctypes.c_long()
        self.Height = ctypes.c_long()
        self.BitsPerPixel = ctypes.c_int()
        self.colorformat = ctypes.c_int()

        self.running = True

    def run(self):
        self.ic.IC_StartLive(self.camera, 0)
        while self.running:
            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
                # Query the values
                self.ic.IC_GetImageDescription(self.camera, self.Width, self.Height, self.BitsPerPixel, self.colorformat)

                 # Calculate the buffer size
                self.bpp = int(self.BitsPerPixel.value / 8.0 )
                self.buffer_size = self.Width.value * self.Height.value * self.BitsPerPixel.value

                # Get the image data
                imagePtr =  self.ic.IC_GetImagePtr(self.camera)

                imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_ubyte * self.buffer_size))

                # Create the numpy array
                img = np.ndarray(buffer = imagedata.contents,
                        dtype = np.uint8,
                        shape = (self.Height.value,
                                self.Width.value,
                                self.bpp))

                # correct channel order                                
                img[:, :, :] = img[:, :, ::-1]

                qimage = QImage(img.data, img.shape[1], img.shape[0], img.strides[0],  QImage.Format_RGB888)
                self.Pixmap_display.emit(qimage)
      
    def resume(self):
        self.running = True
    
    def pause(self):
        self.running = False

class DevConnectionState(QThread):
    dev_connection = pyqtSignal(bool, bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.camera = parent.camera
        self.trig = parent.trig
        self.ic = parent.ic

        self.camera_state = False
        self.trig_state = False

        self.running = True

    def run(self):
        while self.running:
            try:
                print(self.camera, self.trig)
            except:
                print('asdfasdfasdfasdf')
            # Check camera connection state
            if self.ic.IC_IsDevValid(self.camera):
                self.camera_state = True
            else:
                self.camera_state = False

            # Check trigger device connection state
            if self.trig is not None:
                self.trig_state = True
            else:
                self.trig_state = False
            
            # Update event loop
            self.dev_connection.emit(self.camera_state, self.trig_state)
            print(self.camera_state, self.trig_state, '\n')
            # check device connection state for every 5 sec
            time.sleep(3)
    
    def update_state(self, parent):
        self.camera = parent.camera
        self.trig = parent.trig

    def pause(self):
        self.running = False