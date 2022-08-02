import threading
import datetime
import csv
from os.path import join

from kivy.logger import Logger

from hardwareSupport.pivy_camera import CameraSupport
from hardwareSupport.hardwareSupport import TempSensor


class Experiment(threading.Thread):

    def __init__(self, interface):
        super().__init__(name='experiment')
        self.interface = interface

        # store the ledMatrix
        self.ledMatrix = self.interface.ledMatrix

        # instantiate the temperature/humidity sensor objects
        self.tempSensor = TempSensor(interface.teensy_config)

        # use the process_manager created in the interface class to store a few lists
        self.motion_list = self.interface.process_manager.list()
        self.motion_list_lock = self.interface.process_manager.Lock()
        self.egg_count_list = self.interface.process_manager.list()
        self.egg_count_list_lock = self.interface.process_manager.Lock()

        # instantiate the camera object
        self.piCam = CameraSupport(interface._camera._camera, interface.config_file, self.interface.imaging_params,
                                   self.interface.timelapse_option, self.ledMatrix,
                                   self.interface.stop_event, self.interface.stop_cam,
                                   self.interface.video_length, self.exp_end,
                                   self.motion_list, self.motion_list_lock,
                                   self.egg_count_list, self.egg_count_list_lock)


        # self.t_motion_queue_check = threading.Thread(name='motion_queue_check', target=self.check_queue)
        Logger.info('Experiment: start time is %s' % self.exp_start.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: end time is %s' % self.exp_end.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: Initialization complete')

    def run(self):
        # start updater process, end-of-experiment timer thread, and camera thread
        # self.update_process.start()
        # self.t_motion_queue_check.start()
        self.piCam.start()
        Logger.info('Experiment: Threads and processes started')

