import multiprocessing
import time
import math
from copy import deepcopy
from statistics import mean
from kivy.logger import Logger
import threading
from subprocess import Popen, TimeoutExpired
from os.path import join
from fileTransfer import ManageLocalFiles
from googleapiclient.errors import HttpError
import configparser
import random


class Updater(multiprocessing.Process):

    def __init__(self, config_file, led_matrix, temp_sensor, sheet, motion_list,
                 motion_list_lock, egg_count_list, egg_count_list_lock, max_difference):
        super(Updater, self).__init__()
        config = configparser.ConfigParser()
        config.read(config_file)
        self.use_teensy = bool(int(config['LED matrix']['use_teensy']))
        Logger.debug('Updater: self.use_teensy is ' + str(self.use_teensy))
        self.ledMatrix = led_matrix
        self.tempSensor = temp_sensor
        self.sheet = sheet
        self.is_driving_system = bool(int(config['main image processing']['is_driving_system']))
        self.exp_length = int(float(config['experiment settings']['experimentlength']))
        self.timelapse_option = config['LED matrix']['timelapse_options']
        self.motion_list = motion_list
        self.motion_list_lock = motion_list_lock
        self.egg_count_list = egg_count_list
        self.egg_count_list_lock = egg_count_list_lock
        self.cur_row = self.sheet.start_row
        self.cur_row_lock = threading.Lock()
        self.local_savepath = config['experiment settings']['local_exp_path']
        self.remote_savepath = config['experiment settings']['remote_exp_path']
        self.rclone_name = config['experiment settings']['rclone_remote_name']

        self.image_processing_mode = config['main image processing']['image_processing_mode']
        self.motion_with_feedback = bool(int(config['main image processing']['motion_with_feedback']))
        self.num_pixel_threshold = int(config['image delta']['num_pixel_threshold'])
        self.nn_motion_thresh = float(config['neural net']['nn_distance_thresh'])
        self.nn_count_eggs = bool(int(config['neural net']['nn_count_eggs']))
        self.max_difference = max_difference
        self.motion_average = 0

        # check led_on_time to make sure it's less than time resolution of google spreadsheet
        # if it's more than the google sheets time resolution, set it equal to the google sheets resolution
        # in seconds
        self.led_on_time = int(config['main image processing']['led_on_time'])
        if self.led_on_time > self.sheet.time_res:
            self.led_on_time = self.sheet.time_res
        Logger.info('Updater: LED on time is %s seconds' % self.led_on_time)
        # these parameters will be useful for systems where we're doing online perturbations
        self.check_led_dosage_interval = int(config['main image processing']['check_dosage_interval'])
        # sleep_percent starts as a guess as to percent of time in quiescence over the dosage interval
        self.sleep_percent = int(config['main image processing']['sleep_prior'])
        self.paired_led_dosage_percent = self.sleep_percent
        self.led_dosage_percent = self.sleep_percent
        self.check_counter = 0
        # get the maximum percent light exposure
        self.max_exposure = int(config['main image processing']['max_exposure'])
        # reportedly, WT worms spend ~ 90% of their development dwelling, but LED dosages >30% tend to
        # kill animals early in life, so we will only turn the blue LEDs on ~1/3 of the time when we
        # don't detect movement
        self.dwell_dosage_correction = (self.max_exposure/90)*100
        Logger.info('Updater: Dosage correction for dwelling: %s' % self.dwell_dosage_correction)

        self.data = {}
        random.seed()
        self.stop_event = threading.Event()
        Logger.debug('Updater: update process initialized')

    def run(self):
        Logger.debug('Updater: update process running')
        start_time = time.time()
        # perform the first update right away
        # get next set of params as a dict.
        next_params, success = self.sheet.get_params(self.cur_row)
        next_params['opto_on'] = str(0)
        Logger.debug('Updater: Next parameters are: %s' % next_params)
        Logger.info('Updater: Start time is: %s', start_time)
        self.update(next_params)
        with self.cur_row_lock:
            self.cur_row += 1
        # create threaded timers for updating experiment hardware parameters, uploading files
        t_timer = RepeatingTimer(self.sheet, start_time, self.exp_length, self.update, self.stop_event,
                                 self.cur_row, self.cur_row_lock)
        t_timer.start()

        t_timer.join()
        Logger.debug('Updater: update timer thread joined')
        return

    def update(self, next_params):

        # when next timepoint is reached, update all parameters, record data to google sheets
        if self.image_processing_mode != 'None':
            # grab the current motion list
            with self.motion_list_lock:
                motion_list = deepcopy(self.motion_list[:])
                self.motion_list[:] = []
            # use motion list to decide whether to turn the leds on
            if self.image_processing_mode == 'image delta':
                next_params['opto_on'] = self.image_delta_motion_decision(motion_list)

            elif self.image_processing_mode == 'neural net':
                next_params['opto_on'] = self.neural_net_motion_decision(motion_list)
                if self.nn_count_eggs:
                    with self.egg_count_list_lock:
                        egg_count = mean(self.egg_count_list[:])
                        self.data['egg_count'] = egg_count
                        self.egg_count_list.clear()

            self.data['motion'] = self.motion_average
            self.data['opto_on'] = next_params['opto_on']

        if self.timelapse_option == 'None' and self.use_teensy:
            Logger.debug("Updater: updating with next parameters %s" % next_params)
            led_commands = [{'matrix_mode': 'opto', 'is_on': next_params['opto_on']},
                            {'matrix_mode': 'set_color', 'color': ';'.join(
                [next_params['matrix_r'], next_params['matrix_g'], next_params['matrix_b']])},
                            {'matrix_mode': 'set_radius', 'radius': next_params['radius']},
                            {'matrix_mode': next_params['imaging_mode']}]

            self.ledMatrix.send_command(led_commands)
            Logger.debug('LED Matrix: tried to send command Updater.py line 128')
            #
            if next_params['opto_on'] == '1':
                led_commands = [{'matrix_mode': 'opto', 'is_on': str(0)}]
                led_timer = threading.Timer(self.led_on_time, self.ledMatrix.send_command, args=[led_commands])
                Logger.debug('LED Matrix: tried to send command Updater.py line 133')
                led_timer.start()
                Logger.info('Updater: LEDs cycled off')

        # TODO pressure system control
        # try:
        #     command = "https://api.particle.io/v1/devices/" + particle_device_id + "/" + next_params['valve1'] + \
        #               ' -d arg=' + next_params['valve1'] + ' -d access_token=' + particle_token
        #     subprocess.run("curl", command)
        # except:
        #     pass

        try:
            # get temperature and humidity reading
            if self.use_teensy:
                self.data, success = self.tempSensor.receive_serial(self.data)
                Logger.debug('trying to get temp from teensy 148')
            else:
                self.data, success = self.tempSensor.get_temperature_humidity(self.data)
                if success:
                    Logger.debug('TempSensor: Got temp from GPIO')
                else:
                    Logger.debug('TempSensor: failed to get temp from GPIO')
            counter = 0
            while not success and counter <= 3:
                if self.use_teensy:
                    self.data, success = self.tempSensor.receive_serial(self.data)
                else:
                    self.data, success = self.tempSensor.get_temperature_humidity(self.data)
                    if success:
                        Logger.debug('TempSensor: Got temp from GPIO')
                    else:
                        Logger.debug('TempSensor: failed to get temp from GPIO, trying again')

                counter +=1

            # write motion data, temp, and humidity to google sheet
            self.write_data_to_sheet()

            # upload new files to dropbox
            self.upload_to_remote()

        finally:
            # make sure row count gets updated even if writing to sheet isn't successful
            with self.cur_row_lock:
                self.cur_row += 1
            Logger.debug('Updater: finishing this update')

    def write_data_to_sheet(self):
        columns = sorted(self.sheet.data_col_dict.values())
        cell_range = columns[0] + str(self.cur_row) + ':' + columns[-1]
        list = [None]*len(columns)
        for (k, v) in self.sheet.data_col_dict.items():
            # reorder so that the value goes from earliest in alphabet to latest
            idx = columns.index(v)
            list[idx] = self.data[k]
            # Logger.debug('Updater: data %s has data type %s' % (k, type(self.data[k])))

        values = [
            list,
            # Additional rows ...
        ]
        body = {
            'values': values
        }
        self.sheet.write_sheet(body, cell_range=cell_range)

    def get_paired_dosage(self):
        paired_led_dosage = self.sheet.read_sheet(cell_range=self.sheet.led_dosage_cell,
                                                  spreadsheet_tab=self.sheet.paired_spreadsheet_range)
        try:
            return float(paired_led_dosage[0][0])
        except ValueError:
            return 0

    def get_dosage(self):
        led_dosage = self.sheet.read_sheet(cell_range=self.sheet.led_dosage_cell,
                                           spreadsheet_tab=self.sheet.spreadsheet_range)
        try:
            return float(led_dosage[0][0])
        except ValueError:
            Logger.debug('Updater: unable to get led dosage')
            return 0

    def upload_to_remote(self):
        # upload video folder
        source = join(self.local_savepath, 'videos/')
        dest = ':'.join([self.rclone_name, join(self.remote_savepath, 'videos/')])
        Logger.debug('Upload: Source folder %s' % source)
        Logger.debug('Upload: Destination folder %s' % dest)
        timeout_length = self.sheet.time_res - 10
        try:
            p = Popen(["rclone", "copy", source, dest])
            p.wait(timeout=timeout_length)
        except OSError:
            Logger.debug('Updater: Cannot upload videos to remote')
        except TimeoutExpired:
            p.kill()
            Logger.debug('Updater: video upload to remote had TimeoutExpired error')
        except Exception as ex:
            Logger.debug(ex)
            raise Exception("Hi")

        ManageLocalFiles.cleanup_files(source, join(self.remote_savepath, 'videos'), self.rclone_name)

        # upload image folder
        source = join(self.local_savepath, 'images/')
        dest = ':'.join([self.rclone_name, join(self.remote_savepath, 'images/')])
        Logger.debug('Upload: Source folder %s' % source)
        Logger.debug('Upload: Destination folder %s' % dest)
        try:
            p = Popen(["rclone", "copy", source, dest])
            p.wait(timeout=timeout_length)
        except OSError:
            Logger.debug('Updater: Cannot upload images to remote')
        except TimeoutExpired:
            p.kill()
        # while experiment is running, don't delete .h5 file! it will only exist if user chooses to save processed data
        # from neural net processing
        ManageLocalFiles.cleanup_files(source,
                                       join(self.remote_savepath, 'images'),
                                       self.rclone_name,
                                       exclude_ext='.h5')

    def neural_net_motion_decision(self, motion_list):
        # set up a default opto_on to return
        opto_on = str(0)

        if len(motion_list) > 0:
            self.motion_average = float(mean(motion_list))
        else:
            self.motion_average = 'None'

        # update opto_on based on motion if this is the driving system
        if self.is_driving_system:
            if self.motion_average != 'None':
                # if worm's movement is above the set threshold, turn the light off
                if self.motion_average > self.nn_motion_thresh or not self.motion_with_feedback:
                    opto_on = str(0)
                else:
                    rand_int = random.randint(1, 100)
                    if rand_int <= self.dwell_dosage_correction:
                        opto_on = str(1)
                    else:
                        opto_on = str(0)
            else:
                opto_on = str(0)

        # if this isn't the driving system
        else:
            self.check_counter += 1
            if self.check_counter == self.check_led_dosage_interval:
                # these assume led duty cycle is the same and total experiment time will be the same
                self.paired_led_dosage_percent = self.get_paired_dosage()
                self.led_dosage_percent = self.get_dosage()
                Logger.info("Updater: paired dosage is %s, this system's dosage is %s" %
                            (self.paired_led_dosage_percent, self.led_dosage_percent))
                # adjust initial sleep percent guess - if this is > 100 or < 0, this should still work
                self.sleep_percent = self.paired_led_dosage_percent + \
                    (self.paired_led_dosage_percent - self.led_dosage_percent)
                Logger.info("Updater: new sleep guess is %s" % self.sleep_percent)
                self.check_counter = 0

            rand_int = random.randint(1, 100)
            if rand_int <= self.sleep_percent and self.motion_with_feedback:
                # turn on the light
                opto_on = str(1)
            else:
                opto_on = str(0)
        return opto_on

    def image_delta_motion_decision(self, motion_list):
        # set up a default opto_on to return
        opto_on = str(0)

        if len(motion_list) > 0:
            # the upper bound is mostly to account for led illumination
            # drastically changing the delta image calculation
            self.motion_average = float(mean(motion_list))
            if self.motion_average > self.max_difference:
                # the upper bound is mostly to account for led illumination
                # drastically changing the delta image calculation
                self.motion_average = 'Above max'
        else:
            self.motion_average = 'None'

        # update opto parameters based on motion (but only if this is the driving system)
        if self.is_driving_system:
            if self.motion_average != 'None' and self.motion_average != 'Above max':
                # currently configured to turn light on when motion is low
                if (self.motion_average > self.num_pixel_threshold) or not self.motion_with_feedback:
                    opto_on = str(0)
                else:
                    rand_int = random.randint(1, 100)
                    if rand_int <= self.dwell_dosage_correction:
                        opto_on = str(1)
                    else:
                        opto_on = str(0)
            elif self.motion_average == 'None' or self.motion_average == 'Above max':
                opto_on = str(0)

            # if we exceed the max exposure percent, keep the light off
            if self.led_dosage_percent > self.max_exposure:
                opto_on = str(0)
                Logger.info('Updater: exceeded max exposure')

        # update opto parameters based on the paired system's led dosage
        elif not self.is_driving_system:
            self.check_counter += 1
            if self.check_counter == self.check_led_dosage_interval:
                self.paired_led_dosage_percent = self.get_paired_dosage()
                self.led_dosage_percent = self.get_dosage()
                Logger.info("Updater: paired dosage is %s, this system's dosage is %s" %
                            (self.paired_led_dosage_percent, self.led_dosage_percent))
                # adjust initial sleep percent guess - if this is > 100 or < 0, this should still work
                self.sleep_percent = self.paired_led_dosage_percent + \
                                     (self.paired_led_dosage_percent - self.led_dosage_percent)
                Logger.info("Updater: new sleep guess is %s" % self.sleep_percent)
                self.check_counter = 0

            rand_int = random.randint(1, 100)
            if rand_int <= self.sleep_percent and self.motion_with_feedback:
                # turn on the light
                opto_on = str(1)
            else:
                opto_on = str(0)

        return opto_on


class RepeatingTimer(threading.Thread):
    def __init__(self, sheet, start_time, exp_length, function, stop_event, cur_row, cur_row_lock):
        super(RepeatingTimer, self).__init__(name='t_update')
        self.sheet = sheet
        self.start_time = start_time
        self.exp_length = exp_length
        self.interval = self.sheet.time_res
        Logger.debug('Repeating Timer: interval is %d seconds' % self.interval)
        Logger.debug('Repeating Timer: experiment length is %d minutes' % self.exp_length)
        self.function = function
        self.stop_event = stop_event
        self.cur_row = cur_row
        self.cur_row_lock = cur_row_lock
        # update parameters before the first call
        success = False
        counter = 0
        with self.cur_row_lock:
            while not success and counter < 4:
                self.args, success = self.sheet.get_params(self.cur_row)
                counter += 1
            self.cur_row += 1
        self.default_args = self.args
        self.update_time_gen = self.update_time()
        Logger.info('Repeating Timer: initialized')

    def run(self):
        while True:
            try:
                while not self.stop_event.wait(next(self.update_time_gen) - time.time()):
                    Logger.info('Repeating Timer: update call is coming')

                    success = False
                    counter = 0
                    # update parameters after every call
                    with self.cur_row_lock:
                        while not success and counter < 4:
                            self.args, success = self.sheet.get_params(self.cur_row)
                            counter += 1
                        self.cur_row += 1
                    try:
                        if self.args is not None:
                            t_update = threading.Thread(name='update', target=self.function, args=(self.args,))
                            t_update.start()
                        else:
                            t_update = threading.Thread(name='update', target=self.function, args=(self.default_args,))
                            t_update.start()
                    except OSError:
                        Logger.debug('Repeating Timer: cannot update this round, likely a memory problem')
            except StopIteration:
                Logger.info('Repeating Timer: ending repeating timer')
                self.stop()
                return

    def update_time(self):
        i = 1
        while i < math.ceil(self.exp_length * 60 / self.interval):
            yield (self.start_time + i * self.interval)
            i += 1

    def stop(self):
        self.stop_event.set()
