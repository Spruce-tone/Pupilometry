from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes


ic = ctypes.cdll.LoadLibrary('./lib/tisgrabber_x64.dll')


class LiveDisplay(QThread):
    Pixmap_display = pyqtSignal(QImage)

    def run(self):
        tis.declareFunctions(ic)
        ic.IC_InitLibrary(0)
        hGrabber = tis.openDevice(ic)

        ic.IC_StartLive(hGrabber, 0)

        Width = ctypes.c_long()
        Height = ctypes.c_long()
        BitsPerPixel = ctypes.c_int()
        colorformat = ctypes.c_int()
        # Query the values
        ic.IC_GetImageDescription( hGrabber, Width, Height, BitsPerPixel, colorformat )

        # Calculate the buffer size
        bpp = int( BitsPerPixel.value / 8.0 )
        buffer_size = Width.value * Height.value * BitsPerPixel.value

        while True:
            if ic.IC_SnapImage(hGrabber, 2000) == tis.IC_SUCCESS:
        
                # Get the image data
                imagePtr =  ic.IC_GetImagePtr(hGrabber)

                imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_ubyte * buffer_size))

                # Create the numpy array
                img = np.ndarray(buffer = imagedata.contents,
                        dtype = np.uint8,
                        shape = (Height.value,
                                Width.value,
                                bpp))

                # correct channel order                                
                img[:, :, :] = img[:, :, [2, 1, 0]]

                qimage = QImage(img.data, img.shape[1], img.shape[0], img.strides[0],  QImage.Format_RGB888)
                self.Pixmap_display.emit(qimage)