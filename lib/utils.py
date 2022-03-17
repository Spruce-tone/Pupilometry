import numpy as np
from typing import Tuple
import logging

import logging.config
import os

if not os.path.isdir('./logs'):
    os.makedirs('./logs', exist_ok=True)
    
def find_circle(dlc_output: np.ndarray) -> Tuple[np.ndarray, float, float, int]:
    '''
    ----------
    Input Args
    -----------
    dlc_output : ndarray (2D, num_keypoint x 3)
        output from DeepLabCut model
        [coord x, coord y, probability]

    ----------
    Return
    -----------
    center : np.ndarray
        x, y coordinates for center of circle
    diameter : float
        diameter of circle  
    probability : float
        averaged key point recognition probability
    num_points : int
        the number of key points 
    '''
    assert type(dlc_output)==np.ndarray, f'Input must be numpy array'

    coords = dlc_output[:, :-1] # key points x, y coordinated
    probability = dlc_output[:, -1].mean() # key point recognition probability
    num_points = coords.shape[0] # Number of key points

    # to find the diameter and center of circle, Ac=b must be solved
    # (x - xc)^2 + (y - yc)^2 = r^2 (circle equation)
    # c0 + c1x + c2y = x^2 + y^2
    # c0 = r^2 - xc^2, c1 = 2xc, c2 = 2yc
    # vector c = [c0, c1, c2].T
    # the solution vector c that has least squared error, c^ = argmin_c |b - Ac|^2 
    # c^ = (A'A)^-1(A'b), (A' = transpose A)
    A = np.concatenate([np.ones((num_points, 1)), coords], axis=1)
    b = (A**2)[:, 1:].sum(axis=1)
    c = np.linalg.inv(A.T.dot(A)).dot(A.T).dot(b)

    xc = c[1] / 2
    yc = c[2] / 2
    center = np.array([xc, yc])
    diameter = np.sqrt(c[0] + xc**2 + yc**2)*2

    return center, diameter, probability, num_points

def make_circle(center: np.ndarray, diameter, num_sample: int=256) -> np.ndarray:
    '''
    ----------
    Input Args
    -----------
    center : np.ndarray
        x, y coordinates for center of circle np.array([xc, yc])
    diameter : np.float
        diameter of circle  
    num_sample : int
        number of points in circle

    ----------
    Return
    -----------
    circle_points : np.ndarray
        points in circle
    '''
    theta = np.linspace(0, 2 * np.pi, num_sample)
    x = diameter/2 * np.cos(theta)
    y = diameter/2 * np.sin(theta)
    circle_points = np.vstack((x, y)).T + center
    return circle_points



        
LOGGING_CONFIG = {
    'version': 1,
    'loggers': {
        'info': {  
            'level': 'DEBUG',
            'handlers': ['info_console_handler', 'debug_rotating_file_handler', 'error_file_handler'],
        },
    },
    
    'handlers': {
        'info_console_handler': {
            'level': 'INFO',
            'formatter': 'info_format',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },

        'debug_rotating_file_handler': {
            'level': 'DEBUG',
            'formatter': 'debug_format',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': './logs/info.log',
            'mode': 'w',
            'maxBytes': 1048576,
            'backupCount': 10
        },

        'error_file_handler': {
            'level': 'ERROR',
            'formatter': 'debug_format',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': './logs/error.log',
            'mode': 'w',
            'maxBytes': 1048576,
            'backupCount': 10
        },

    },

    'formatters': {
        'info_format': {
            'format': '[%(levelname)s | %(asctime)s | %(filename)s | %(funcName)s] (line %(lineno)d) %(message)s :: %(name)s logger'
        },
        'debug_format': {
            'format': '[%(levelname)s | %(asctime)s| %(module)s | %(filename)s | %(funcName)s]\n (line %(lineno)d) %(message)s :: %(name)s logger \n'
        },
    },

}

class CustomLogger():
    def __init__(self):
        self.LOGGER_CONFIG_PATH = "./lib/logger_config.json"
        self.LOG_FILE_PATH = "./logs"
        if os.path.isdir(self.LOG_FILE_PATH):
            os.makedirs(self.LOG_FILE_PATH, exist_ok=True)
        
        self.info_logger = self._get_logger('info')

    def _get_logger(self, logger_name: str):
        """
        make logger instance from logger config file

        ------------------------------
        Input Args:
            logger_name : str
                enter logger name
        """
        logging.config.dictConfig(LOGGING_CONFIG)
        return logging.getLogger(logger_name)

