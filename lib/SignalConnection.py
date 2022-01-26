from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes
import time


class LiveDisplay(QThread):
    Pixmap_display = pyqtSignal(QImage)
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.camera = parent.camera
        self.ic = parent.ic

        self.Width = ctypes.c_long()
        self.Height = ctypes.c_long()
        self.BitsPerPixel = ctypes.c_int()
        self.colorformat = ctypes.c_int()
        
        self.running = True

    def run(self):
        # start camera for live
        self.ic.IC_StartLive(self.camera, 0)

        # Query the values
        self.ic.IC_GetImageDescription(self.camera, self.Width, self.Height, self.BitsPerPixel, self.colorformat)
        
        # Calculate the buffer size    
        self.bpp = int(self.BitsPerPixel.value / 8.0 )
        self.buffer_size = self.Width.value * self.Height.value * self.BitsPerPixel.value
        
        while self.running:
            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
               

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
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait(10000)

class RefreshDevState(QThread):
    refresh_dev_state = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.running = True

    def run(self):
        while self.running:
            # emit signal for refresh device state
            self.refresh_dev_state.emit(True)
            time.sleep(2)

    def pause(self):
        self.running = False

    def stop(self):
        self.running = False
        self.quit()
        self.wait(10000)

class TriggeredRecording(QThread):
    recording_termination = pyqtSignal()
    save_img = pyqtSignal(int, np.ndarray)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.running = True
        self.keep_recording = True

        self.camera = parent.camera
        self.ic = parent.ic

        self.Width = ctypes.c_long()
        self.Height = ctypes.c_long()
        self.BitsPerPixel = ctypes.c_int()
        self.colorformat = ctypes.c_int()

    def run(self):
        while self.running:
            # receive TTL signal
            # default data value = [254] when trigger receiving device is connected to the TTL source using BNC cable
            _, data = self.parent.trig.readAny(self.parent.startPort, self.parent.portCount)
            
            # when the device receive TTL signal, the data value becaomes [255]  
            if data==[255]:
                self.running = False

        # start camera for live
        self.ic.IC_StartLive(self.camera, 0)

        # Query the values
        self.ic.IC_GetImageDescription(self.camera, self.Width, self.Height, self.BitsPerPixel, self.colorformat)
        
        # Calculate the buffer size    
        self.bpp = int(self.BitsPerPixel.value / 8.0 )
        self.buffer_size = self.Width.value * self.Height.value * self.BitsPerPixel.value
              

        # loop_start = time.time()
        for idx in range(self.parent.frames):
            frame_start = time.time()
            if not self.keep_recording:
                return

            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
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
                self.save_img.emit(idx, img)

            frame_end = time.time()
            capture_duration = frame_end - frame_start
            
            # give time delay to adjust frame rate
            if capture_duration < (1 / self.parent.frame_rate):
                sleep_time = (1/self.parent.frame_rate) - capture_duration
                time.sleep(sleep_time)
            
        # loop_end = time.time()
        # loop_dur = loop_end - loop_start
        # calculate frame rate
        # print(f'finish_imaging : {loop_end - loop_start:.5f} sec')
        # print(f'frame rates : {self.parent.frames / (loop_end - loop_start):.5f} fps')
        # print(f'error {loop_dur - 1 / self.parent.frame_rate * self.parent.frames:.5f} s')
        # print(f'error {100 * (loop_dur - 1 / self.parent.frame_rate * self.parent.frames) / (1 / self.parent.frame_rate * self.parent.frames):.05f} %')

        self.recording_termination.emit()

    def pause(self):
        self.running =False
    
    def stop(self):
        self.running = False
        self.keep_recording = False
        self.quit()
        self.wait(10000)


class StartRecording(QThread):
    recording_termination = pyqtSignal()
    save_img = pyqtSignal(int, np.ndarray)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.running = True
        self.keep_recording = True

        self.camera = parent.camera
        self.ic = parent.ic

        self.Width = ctypes.c_long()
        self.Height = ctypes.c_long()
        self.BitsPerPixel = ctypes.c_int()
        self.colorformat = ctypes.c_int()

    def run(self):
        # start camera for live
        self.ic.IC_StartLive(self.camera, 0)

        # Query the values
        self.ic.IC_GetImageDescription(self.camera, self.Width, self.Height, self.BitsPerPixel, self.colorformat)
        
        # Calculate the buffer size    
        self.bpp = int(self.BitsPerPixel.value / 8.0 )
        self.buffer_size = self.Width.value * self.Height.value * self.BitsPerPixel.value
              
        for idx in range(self.parent.frames):
            frame_start = time.time()
            if not self.keep_recording:
                return

            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
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
                self.save_img.emit(idx, img)

            frame_end = time.time()
            capture_duration = frame_end - frame_start
            
            # give time delay to adjust frame rate
            if capture_duration < (1 / self.parent.frame_rate):
                sleep_time = (1/self.parent.frame_rate) - capture_duration
                time.sleep(sleep_time)

        self.recording_termination.emit()

    def pause(self):
        self.running =False
    
    def stop(self):
        self.running = False
        self.keep_recording = False
        self.quit()
        self.wait(10000)