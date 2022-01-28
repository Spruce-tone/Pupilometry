from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes, time
from lib.utils import find_circle, make_circle
from typing import Dict

class LiveDisplay(QThread):
    Pixmap_display = pyqtSignal(dict) # captured image

    # triggered recording
    recording_termination = pyqtSignal()
    save_img = pyqtSignal(int, np.ndarray)

    # manual recording mode
    recording_termination = pyqtSignal()
    save_img = pyqtSignal(int, np.ndarray)

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
        
        # moving avg filter for frame rate
        # initial avg value is 30 Hz, sampling = 25
        self.live_fps = np.ones(25)*30

        # triggered recording
        self.keep_recording = True

    def run(self):
        self.live_display_mode()

    def resume(self):
        self.running = True
    
    def pause(self):
        self.running = False
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait(10000)

    def _ready_camera(self):
        # start camera for live
        self.ic.IC_StartLive(self.camera, 0)

        # Query the values
        self.ic.IC_GetImageDescription(self.camera, self.Width, self.Height, self.BitsPerPixel, self.colorformat)
        
        # Calculate the buffer size    
        self.bpp = int(self.BitsPerPixel.value / 8.0 )
        self.buffer_size = self.Width.value * self.Height.value * self.BitsPerPixel.value

    def _get_sanp(self) -> np.ndarray:
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

        # qimage for display
        qimage = QImage(img.data, img.shape[1], img.shape[0], img.strides[0],  QImage.Format_RGB888)

        return img, qimage
                

    def live_display_mode(self):
        self._ready_camera()
        
        while self.running:
            # measure frame rate
            loop_start = time.time()
            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
                
                img, qimage = self._get_sanp()

                # signal container
                live_signal = {}

                if self.parent.show_circle.isChecked():
                    dlc_output = self.parent.dlclive.get_pose(img)
                    center, radius, probability = find_circle(dlc_output)
                    if probability >= self.parent.fit_threshold:
                        live_signal['center'] = center
                        live_signal['radius'] = radius

                live_signal['image'] = qimage
                

                loop_end = time.time()
                duration = loop_end - loop_start
                fps = 0 if duration <= 0 else 1/duration
                self.live_fps[0:-1] = self.live_fps[1:]
                self.live_fps[-1] = fps

                live_signal['frame_rate'] = self.live_fps.mean()
                self.Pixmap_display.emit(live_signal)

    def triggered_recording_mode(self):
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

    def manual_recording_mode(self):
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