import threading
import multiprocessing
import datetime
import time
import queue
import csv
from os.path import join

from kivy.logger import Logger

from hardwareSupport.pivy_camera import CameraSupport
from fileTransfer import SheetsTransferData
from hardwareSupport.hardwareSupport import TempSensor
import Updater


class Experiment(threading.Thread):

    def __init__(self, interface):
        super().__init__(name='experiment')
        self.interface = interface

        # store the ledMatrix
        self.ledMatrix = self.interface.ledMatrix

        # at beginning of experiment, populate first Date-Time field in google sheet
        # with 'now' and propagate to end of the experiment field. Experimental Time should
        # be already filled
        # if you change the google sheets format, make sure to provide the
        # correct column-to-parameter mapping below in param_col_dict and the correct cell for
        # time resolution of experiment
        param_col_dict = {'imaging_mode': 'C', 'matrix_r': 'D', 'matrix_g': 'E',
                          'matrix_b': 'F', 'radius': 'G', 'opto_on': 'H'}
        data_col_dict = {'temperature': 'I', 'humidity': 'J'}
        if self.interface.image_processing_mode != 'None':
            data_col_dict['opto_on'] = 'H'
            data_col_dict['motion'] = 'K'
            if self.interface.image_processing_mode == 'neural net':
                if self.interface.nn_count_eggs:
                    data_col_dict['egg_count'] = 'L'
        time_res_cell = 'B2'
        led_dosage_cell = 'J2'
        # we'll make a shared resource that contains the current row of the spreadsheet so that the motion updater
        # will know where we are.
        self.sheet = SheetsTransferData.SheetsTransferData(interface.spreadsheet_id, interface.system_id,
                                                           interface.paired_system_id, param_col_dict, data_col_dict,
                                                           time_res_cell, led_dosage_cell, interface.exp_code)

        # clear any old data out of the data columns of the google spreadsheet
        for (k, v) in data_col_dict.items():
            self.sheet.clear_data(v)

        # if google sheet format is changed, make sure to provide the right cell
        # to init time to
        self.exp_start = self.sheet.init_time()
        self.exp_end = self.exp_start + datetime.timedelta(minutes=interface.explength)

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

        # instantiate the updater process
        self.update_process = Updater.Updater(interface.config_file, self.ledMatrix, self.tempSensor,
                                              self.sheet, self.motion_list, self.motion_list_lock,
                                              self.egg_count_list, self.egg_count_list_lock,
                                              self.piCam.max_difference)

        # self.t_motion_queue_check = threading.Thread(name='motion_queue_check', target=self.check_queue)
        Logger.info('Experiment: start time is %s' % self.exp_start.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: end time is %s' % self.exp_end.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: Initialization complete')

    def run(self):
        # start updater process, end-of-experiment timer thread, and camera thread
        self.update_process.start()
        # self.t_motion_queue_check.start()
        self.piCam.start()
        Logger.info('Experiment: Threads and processes started')

    def write_sheet_to_dbx(self, values):
        local_file = join(self.interface.local_savepath, 'exp_conditions.csv')
        with open(local_file, mode='w') as csv_file:
            writeobj = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in values:
                writeobj.writerow(row)
