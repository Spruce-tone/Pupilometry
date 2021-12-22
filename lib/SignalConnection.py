from PyQt5.QtCore import pyqtSignal, QThread, Qt
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes


class LiveDisplay(QThread):
    Pixmap_display = pyqtSignal(QImage)
    
    def __init__(self, parent, camera, ic):
        super().__init__(parent)
        self.camera = camera
        self.ic = ic

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