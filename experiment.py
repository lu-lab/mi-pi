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
from hardwareSupport.hardwareSupport import TempSensor, LEDMatrix
import Updater


class Experiment(threading.Thread):

    def __init__(self, interface):
        super().__init__(name='experiment')
        self.interface = interface

        # instantiate the ledMatrix
        self.ledMatrix = LEDMatrix(interface.teensy_config, color=interface.LEDcolor, radius=interface.matrix_radius,
                                   mode='darkfield', do_timelapse=self.interface.timelapse_option)

        # instantiate the camera object
        self.piCam = CameraSupport(interface._camera._camera, interface.config_file, self.interface.imaging_params,
                                   self.ledMatrix, self.interface.stop_cam, self.interface.video_length)

        # at beginning of experiment, populate first Date-Time field in google sheet
        # with 'now' and propagate to end of the experiment field. Experimental Time should
        # be already filled
        # if you change the google sheets format, make sure to provide the
        # correct column-to-parameter mapping below in param_col_dict and the correct cell for
        # time resolution of experiment
        param_col_dict = {'imaging_mode': 'C', 'matrix_r': 'D', 'matrix_g': 'E',
                          'matrix_b': 'F', 'radius': 'G', 'opto_on': 'H'}
        data_col_dict = {'temperature': 'I', 'humidity': 'J'}
        if self.interface.image_processing_mode != 'None' and interface.is_driving_system:
            data_col_dict['opto_on'] = 'H'
            data_col_dict['motion'] = 'K'
            if self.interface.image_processing_mode == 'image thresholding':
                data_col_dict['area'] = 'L'
        time_res_cell = 'B2'
        led_dosage_cell = 'J2'
        # we'll make a shared resource that contains the current row of the spreadsheet so that the motion updater
        # will know where we are.
        self.sheet = SheetsTransferData.SheetsTransferData(interface.spreadsheet_id, interface.system_id,
                                                           interface.paired_system_id, param_col_dict, data_col_dict,
                                                           time_res_cell, led_dosage_cell, interface.exp_code)

        # if google sheet format is changed, make sure to provide the right cell
        # to init time to
        self.exp_start = self.sheet.init_time()
        self.exp_end = self.exp_start + datetime.timedelta(minutes=interface.explength)

        # instantiate the temperature/humidity sensor objects
        self.tempSensor = TempSensor(interface.teensy_config)

        # queue for motion information from camera class
        self.cam_queue = queue.Queue(maxsize=1)
        self.mgr = multiprocessing.Manager()
        self.motion_list = self.mgr.list()
        self.update_process = Updater.Updater(interface.config_file, self.ledMatrix, self.tempSensor,
                                              self.sheet, self.motion_list, self.piCam.max_difference)
        if self.interface.timelapse_option == 'None':
            self.t_camera = threading.Thread(name='camera', target=self.piCam.capture_video,
                                             args=(self.exp_end, self.cam_queue))
        elif self.interface.timelapse_option == 'linescan':
            self.t_camera = threading.Thread(name='camera', target=self.piCam.linescan_timelapse,
                                             args=(self.exp_end, self.cam_queue))
        elif self.interface.timelapse_option == 'brightfield':
            self.t_camera = threading.Thread(name='camera', target=self.piCam.timelapse,
                                             args=(self.exp_end, self.cam_queue))

        self.t_motion_queue_check = threading.Thread(name='motion_queue_check', target=self.check_queue)
        Logger.info('Experiment: start time is %s' % self.exp_start.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: end time is %s' % self.exp_end.strftime("%H:%M:%S %B %d, %Y"))
        Logger.info('Experiment: Initialization complete')

    def run(self):
        # start updater process, end-of-experiment timer thread, and camera thread
        self.update_process.start()
        self.t_motion_queue_check.start()
        self.t_camera.start()
        Logger.info('Experiment: Threads and processes started')

    def check_queue(self):
        while True:
            if not self.cam_queue.empty():
                motion = self.cam_queue.get()
                Logger.debug('Experiment: motion is %s, time is %s' % (motion, time.time()))
                if motion is None:
                    Logger.debug('Experiment: Poison pill received, exiting')
                    self.cam_queue.task_done()
                    self.cam_queue.join()
                    self.interface.stop_event.set()
                    break
                else:
                    self.motion_list.append(motion)
                    self.cam_queue.task_done()

    def write_sheet_to_dbx(self, values):
        local_file = join(self.interface.local_savepath, 'exp_conditions.csv')
        with open(local_file, mode='w') as csv_file:
            writeobj = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            for row in values:
                writeobj.writerow(row)
