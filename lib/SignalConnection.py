from PyQt5.QtCore import pyqtSignal, QThread
from PyQt5.QtGui import QImage
from lib import tisgrabber as tis
import numpy as np
import ctypes, time
from lib.utils import find_circle
from typing import Tuple
from datetime import datetime

class GetCamImage(QThread):
    # signal for live imaging
    Pixmap_display = pyqtSignal(dict) # captured image

    # signals triggered and manual recording mode
    recording_termination = pyqtSignal() # stop recording
    save_img = pyqtSignal(dict) # save image

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

        # container to store signal
        self.live_signal = {}

        # triggered recording
        self.keep_recording = True

    def run(self):
        if self.parent.recording_type=='LiveDisplay':
            self.live_display_mode()
        elif self.parent.recording_type in ['Triggered', 'Manual']:
            self.recording_mode()

    def resume(self):
        self.running = True
    
    def pause(self):
        self.running = False
    
    def stop(self):
        self.running = False
        self.keep_recording = False
        self.quit()
        self.wait(10000)
    
    def set_recording_mode(self):
        self.stop()
        self.running = True
        self.keep_recording = True
        self.start()

    def _ready_trigger(self):
        '''
        ready TTL signal for triggered recording
        Vmin = 0V, Vmax = 5V, duration > 200 ms
        TTL on state, data = 255
        TTL off state, data = 254
        '''
        self.outlier_check = np.array([0]*100) # to prevent outlier TTL signal, moving average filter

        while self.running:
            # receive TTL signal
            # default data value = [254] when trigger receiving device is connected to the TTL source using BNC cable
            _, data = self.parent.trig.readAny(self.parent.startPort, self.parent.portCount)
            
            self.outlier_check[:-1] = self.outlier_check[1:]
            self.outlier_check[-1] = data[0]-254
            
            # when the device receive TTL signal, the data value becaomes [255]  
            if data==[255] and (self.outlier_check.sum() >= 25):
                self.running = False

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
    
    def _get_circle(self, img: np.ndarray) -> Tuple[float, float, float, np.ndarray]:
        '''
        ----------
        Input Args
        -----------
        img : ndarray (2D image, width x height)
            2D numpy array image  

        ----------
        Return
        -----------
        center : np.ndarray
            x, y coordinates for center of circle
        diameter : np.float
            diameter of circle
        probability : float
            averaged key point recognition probability
        dlc_output : np.ndarray (dimension - No. key points * [x, y, probability])
            key points coordinate and probability  
        '''
        dlc_output = self.parent.dlclive.get_pose(img)
        center, diameter, probability, _ = find_circle(dlc_output)
        return center, diameter, probability, dlc_output

    def _mov_avg_fps(self, start_time: float, end_time: float) -> float:
        imaging_duration = end_time - start_time
        fps = 0 if imaging_duration <= 0 else 1/imaging_duration
        self.live_fps[0:-1] = self.live_fps[1:]
        self.live_fps[-1] = fps
        return self.live_fps.mean()

    def _wait_imaging(self, start_time: float, end_time: float, frame_rate: float):
        '''
        make delay to adjust imaging spped
        '''
        capture_duration = end_time - start_time

        # give time delay to adjust frame rate
        if capture_duration < (1 / frame_rate):
            sleep_time = (1/frame_rate) - capture_duration
            time.sleep(sleep_time)

    def live_display_mode(self):
        self._ready_camera()
        
        while self.running:
            loop_start = time.time() # loop starting time
            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
                # get image from camera
                img, self.live_signal['qimage'] = self._get_sanp()
                self.live_signal['time_stamp'] = datetime.now() 
                
                if self.parent.show_circle.isChecked(): # check dynamic pupil size measurements
                    # get center and diameter of pupil
                    self.live_signal['center'], self.live_signal['diameter'], self.live_signal['probability'], self.live_signal['dlc_output'] = self._get_circle(img) 

            loop_end = time.time() # imaging end time
            self._wait_imaging(loop_start, loop_end, self.parent.frame_rate) # wait to adjust imaging speed
            
            wait_end = time.time() # loop end time (total duration = imaging time + waiting time)
            self.live_signal['frame_rate'] = self._mov_avg_fps(loop_start, wait_end) # get frame rate
            self.Pixmap_display.emit(self.live_signal) # emit image signal to display

    def recording_mode(self):
        if self.parent.recording_type=='Triggered':
            self._ready_trigger()
        self._ready_camera()
              
        for idx in range(self.parent.frames):
            loop_start = time.time() # loop starting time
            if not self.keep_recording:
                return

            if self.ic.IC_SnapImage(self.camera, 2000) == tis.IC_SUCCESS:
                # Get the image data
                img, self.live_signal['qimage'] = self._get_sanp()
                self.live_signal['time_stamp'] = datetime.now()

                if self.parent.show_circle.isChecked(): # check dynamic pupil size measurements
                    # get center and diameter of pupil
                    self.live_signal['center'], self.live_signal['diameter'], _, self.live_signal['dlc_output'] = self._get_circle(img) 


            loop_end = time.time() # imaging end time
            self._wait_imaging(loop_start, loop_end, self.parent.frame_rate) # wait to adjust imaging speed

            wait_end = time.time() # loop end time (total duration = imaging time + waiting time)
            self.live_signal['frame_rate'] = self._mov_avg_fps(loop_start, wait_end) # get frame rate
            self.live_signal['index'] = idx
            self.live_signal['image'] = img

            self.Pixmap_display.emit(self.live_signal) # emit image signal to display
            self.save_img.emit(self.live_signal) # emit image signal to save

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