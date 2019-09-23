'''
Interface for mi-pi
'''

from kivy.app import App
from kivy.clock import mainthread
from kivy.logger import Logger
from kivy.properties import StringProperty, BooleanProperty,\
    ListProperty, NumericProperty, DictProperty, ReferenceListProperty
from kivy.uix.settings import SettingsWithSidebar
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.uix.textinput import TextInput

from settings import expSettings_json, imagingSettings_json, \
    pressureSettings_json, imageProcessingSettings_json
from fileTransfer import ManageLocalFiles
from keys import SYSTEM_IDS, GOOGLE_SPREADSHEET_ID, \
    CURDIR, CONFIG_FILE
from hardwareSupport.hardwareSupport import TeensyConfig, LEDMatrix
import experiment

import os
from os.path import join, basename, exists
from os import makedirs
import string
import random
import time
import datetime
import threading
from shutil import copyfile
import logging
from subprocess import Popen, TimeoutExpired

Logger.setLevel(logging.DEBUG)


class Interface(BoxLayout):
    exp_image_source = StringProperty('icons/experiment_not_prepped.png')
    snapshot_image_source = StringProperty('icons/snapshot_not_prepped.png')
    exp_text = StringProperty('Prep experiment')
    is_exp_running = BooleanProperty(False)
    imaging_params = DictProperty()
    im_res_x = NumericProperty(640)
    im_res_y = NumericProperty(480)
    im_res = ReferenceListProperty(im_res_x, im_res_y)
    stop_event = threading.Event()
    stop_cam = threading.Event()

    def __init__(self, **kwargs):
        super(Interface, self).__init__(**kwargs)
        self.ids.capture_button.disabled = True
        self.ids.start_button.disabled = True
        self.paired_system_id = None
        self._camera = self.ids.camera._camera
        self.config_file = CONFIG_FILE

    def screenshot(self):
        cur_time = time.strftime("%Y%m%d_%H%M%S")
        self.export_to_png('screenshot_{}.png'.format(cur_time))

    def capture_image(self):
        imgdir = join(self.local_savepath, 'images')
        if not os.path.exists(imgdir):
            os.makedirs(imgdir)
        camera = self.ids['camera']
        timestr = time.strftime("%Y%m%d_%H%M%S")
        imgfile = join(imgdir, "IMG_{}.png".format(timestr))
        self._camera._camera.resolution = self.imaging_params['video_resolution']
        self._camera._camera.capture(imgfile)
        Logger.info("Interface: Captured filename %s" % imgfile)
        source = imgfile
        dest = ':'.join([self.rclone_name, '/'.join([self.remote_savepath, 'images', basename(source)])])
        p = Popen(["rclone", "copy", source, dest])
        try:
            p.wait(timeout=2)
        except TimeoutExpired:
            p.kill()
        ManageLocalFiles.cleanup_files(self.local_savepath, self.remote_savepath, self.rclone_name)

    def update_exp_button(self):
        if self.is_exp_running:
            self.stop_event.set()
        elif not self.is_exp_running:
            self.start_experiment()

    def start_experiment(self):
        self.exp_text = 'Experimenting!'
        self.exp_image_source = 'icons/experiment_started.png'
        Logger.info('Interface: Experiment started')
        self.is_exp_running = not self.is_exp_running
        camera = self.ids['camera']
        camera.play = False
        self.set_config()
        threading.Thread(target=self.check_stop).start()
        self.experiment = experiment.Experiment(self)
        self.experiment.start()

    def check_stop(self):
        while True:
            # if the experiment ends
            if self.stop_event.is_set():
                cur_time = time.strftime("%Y/%m/%d %H:%M:%S")
                cur_time = datetime.datetime.strptime(cur_time, "%Y/%m/%d %H:%M:%S")
                if not self.stop_cam.is_set():
                    # if the current time is later than the experiment end time, the experiment ended in the normal way,
                    # so the camera is already closed and we don't have to set the stop_cam event
                    if cur_time > self.experiment.exp_end:
                        is_early = False

                    # the experiment was interrupted early, so the camera isn't closed yet. close it before intitiating
                    # the usual stop sequence
                    else:
                        is_early = True
                        self.stop_cam.set()
                        # the camera will wait until it's done with any video recording and images it's currently
                        # collecting before closing, so we'll wait a while to make sure it has plenty of time to close
                        # in a reasonable manner before calling stop_experiment
                        time.sleep(self.video_length + self.inter_video_interval + 10)

                    self.stop_experiment(is_early)
                    # once stop_experiment has been called once, return so it doesn't accidentally get called
                    # twice!
                    return

    @mainthread
    def stop_experiment(self, is_early):
        # finally, make sure to turn the blue LEDs off at the end of the experiment
        Logger.debug("Interface: updating with final parameters")
        led_commands = [{'matrix_mode': 'opto', 'is_on': str(0)}]
        self.experiment.ledMatrix.send_command(led_commands)

        # the experiment has ended in a regular way.
        if not is_early:
            # join the update process in the proper way
            # self.experiment.t_motion_queue_check.join()
            # Logger.debug('Interface: motion queue closed')
            self.experiment.update_process.join()
            Logger.debug('Interface: update_process closed')

        # the experiment has been ended prematurely
        else:
            # we'll have to terminate the update process
            self.experiment.update_process.terminate()
            Logger.debug('Interface: update_process terminated')

        self.experiment.t_camera.join()
        Logger.debug('Interface: camera closed')

        # grab data from the spreadsheet and write it to a csv file, then save it to the cloud service
        max_row = self.explength + self.experiment.sheet.start_row
        cell_range = 'A1:L' + str(max_row)
        values = self.experiment.sheet.read_sheet(cell_range='A1:L')
        self.experiment.write_sheet_to_dbx(values)

        # copy logs to experiment folder
        app = App.get_running_app()
        log_dir = app.config.get('kivy', 'log_dir')
        log_name = app.config.get('kivy', 'log_name')
        log_path = '/'.join(['.kivy', log_dir, log_name])
        file_to = '/'.join([self.local_savepath, log_name])
        copyfile(log_path, file_to)

        src = self.local_savepath
        dest = self.remote_savepath
        p3 = Popen(
            ["rclone", "copy", join(src, 'images/'), ':'.join([self.rclone_name, join(dest, 'images/')])])
        p2 = Popen(
            ["rclone", "copy", join(src, 'videos/'), ':'.join([self.rclone_name, join(dest, 'videos/')])])
        p1 = Popen(["rclone", "copy", src, ':'.join([self.rclone_name, dest])])
        for p in [p1, p2, p3]:
            try:
                p.wait(timeout=30)
            except TimeoutExpired:
                p.kill()

        ManageLocalFiles.cleanup_files(src, dest, self.rclone_name)
        ManageLocalFiles.cleanup_files(join(src, 'videos/'), join(dest, 'videos/'), self.rclone_name)
        ManageLocalFiles.cleanup_files(join(src, 'images/'), join(dest, 'images/'), self.rclone_name)

        # reset folder names in .ini file for next experiment

        app.config.set('experiment settings', 'local_exp_path', self.top_dir_local)
        app.config.set('experiment settings', 'remote_exp_path', self.top_dir_remote)
        app.config.write()


        # update experiment button (changes button image and text and updates 'is_exp_running')
        self.is_exp_running = False
        self.snapshot_image_source = 'icons/snapshot_not_prepped.png'
        self.exp_image_source = 'icons/experiment_not_prepped.png'
        self.exp_text = 'Experiment over'
        Logger.info('Interface: experiment ended')

    def set_config(self):
        app = App.get_running_app()
        self.system_id = app.config.get('experiment settings', 'systemid')
        paired_system_id = app.config.get('main image processing', 'paired_systemid')
        self.is_driving_system = app.config.get('main image processing', 'is_driving_system')

        self.top_dir_local = app.config.get('experiment settings', 'local_exp_path')
        self.top_dir_remote = app.config.get('experiment settings', 'remote_exp_path')
        # experiment length in minutes
        self.explength = app.config.getint('experiment settings', 'experimentlength')
        self.timelapse_option = app.config.get('LED matrix', 'timelapse_options')
        Logger.debug('Interface: timelapse option is %s' % str(self.timelapse_option))
        self.hc_image_frequency = app.config.getint('LED matrix', 'hc_image_frequency')
        self.LEDcolor = app.config.get('LED matrix', 'ledcolor')
        self.matrix_radius = app.config.getint('LED matrix', 'matrixradius')
        self.led_center = (app.config.getint('LED matrix', 'ledx'), app.config.getint('LED matrix', 'ledy'))
        self.spreadsheet_id = app.config.get('experiment settings', 'google_spreadsheet_id')
        self.rclone_name = app.config.get('experiment settings', 'rclone_remote_name')
        self.teensy_config = TeensyConfig()

        # instantiate the ledMatrix
        self.ledMatrix = LEDMatrix(self.teensy_config, color=self.LEDcolor, radius=self.matrix_radius,
                                   mode='darkfield', center=self.led_center, do_timelapse=self.timelapse_option)

        res_string = app.config.get('main image processing', 'image_resolution')
        im_res = tuple(int(i) for i in res_string.split('x'))
        Logger.debug('Interface: image resolution is %s' % res_string)
        # if self.im_res_x != im_res[0] or self.im_res_y != im_res[1]:
        #     # self._camera._camera.resolution = im_res
        #     self.im_res_x, self.im_res_y = im_res[0], im_res[1]
        self.imaging_params['image_resolution'] = im_res
        self.imaging_params['video_resolution'] = app.config.get('camera settings', 'resolution')
        self.inter_video_interval = app.config.getint('camera settings', 'inter_video_interval')
        self.video_length = app.config.getint('camera settings', 'video_length')
        self.imaging_params['image_frequency'] = app.config.getint('main image processing', 'image_frequency')
        self.imaging_params['delta_threshold'] = app.config.getint('image delta', 'delta_threshold')
        self.imaging_params['num_pixel_threshold'] = app.config.getint('image delta', 'num_pixel_threshold')
        self.image_processing_mode = app.config.get('main image processing', 'image_processing_mode')
        self.imaging_params['image_processing_mode'] = self.image_processing_mode

        thresh_block_size = app.config.getint('image thresholding', 'thresh_block_size')
        thresh_block_size = max(3, thresh_block_size)
        if thresh_block_size % 2 == 0:
            thresh_block_size += 1  # this value must be odd
        self.imaging_params['thresh_block_size'] = thresh_block_size

        self.imaging_params['keep_border_data'] = bool(app.config.getint('image thresholding', 'keep_border_data'))
        self.imaging_params['min_area'] = app.config.getint('image thresholding', 'min_area')
        self.imaging_params['max_area'] = app.config.getint('image thresholding', 'max_area')
        self.imaging_params['dilation_size'] = app.config.getint('image thresholding', 'dilation_size')
        self.imaging_params['xmin'] = app.config.getint('image thresholding', 'xmin')
        self.imaging_params['xmax'] = app.config.getint('image thresholding', 'xmax')
        self.imaging_params['ymin'] = app.config.getint('image thresholding', 'ymin')
        self.imaging_params['ymax'] = app.config.getint('image thresholding', 'ymax')
        self.imaging_params['save_images'] = bool(app.config.getint('main image processing', 'save_images'))

        if paired_system_id in SYSTEM_IDS and self.image_processing_mode != 'None':
            self.paired_system_id = paired_system_id

        if self.is_exp_running:
            self.exp_code = ''.join(random.choice(string.ascii_uppercase + string.digits)for _ in range(8))
            Logger.debug('Interface: experiment code is %s' % self.exp_code)
            self.remote_savepath = self.top_dir_remote + '/'.join([self.system_id, 'data', self.exp_code])
            self.local_savepath = join(self.top_dir_local, self.system_id, 'data', self.exp_code)
            p1 = Popen(["rclone", "mkdir", ':'.join([self.rclone_name, self.remote_savepath])])
            app.config.set('experiment settings', 'remote_exp_path', self.remote_savepath)
            app.config.set('experiment settings', 'local_exp_path', self.local_savepath)
            app.config.write()
            video_save_dir = join(self.local_savepath, 'videos')
            calibrate_save_dir = join(self.local_savepath, 'images')
            if not exists(video_save_dir):
                makedirs(video_save_dir)
            if not exists(calibrate_save_dir):
                makedirs(calibrate_save_dir)
                if self.imaging_params['save_images']:
                    unprocesspath = join(calibrate_save_dir, 'unprocessed')
                    # processpath = join(calibrate_save_dir, 'processed')
                    makedirs(unprocesspath)
                    # makedirs(processpath)
            p2 = Popen(["rclone", "mkdir", ':'.join([self.rclone_name, join(self.remote_savepath, 'videos')])])
            p3 = Popen(["rclone", "mkdir", ':'.join([self.rclone_name, join(self.remote_savepath, 'images')])])
            for p in [p1, p2, p3]:
                try:
                    p.wait(timeout=2)
                except TimeoutExpired:
                    p.kill()
        else:
            self.remote_savepath = self.top_dir_remote + '/'.join([self.system_id, 'data', 'initial'])
            self.local_savepath = join(self.top_dir_local, self.system_id, 'data', 'initial')
            p = Popen(["rclone", "mkdir", ':'.join([self.rclone_name, self.remote_savepath])])

            try:
                p.wait(timeout=2)
            except TimeoutExpired:
                p.kill()

        if not os.path.exists(self.local_savepath):
            os.makedirs(self.local_savepath)

        self.LEDcolor = self.LEDcolor.lstrip('[').rstrip(']')
        self.LEDcolor = self.LEDcolor.replace(',', ';')

        # copy configuration to experiment folder
        file_to = '/'.join([self.local_savepath, basename(CONFIG_FILE)])
        copyfile(CONFIG_FILE, file_to)


class KivycamApp(App):

    def build(self):
        self.settings_cls = SettingsWithSidebar
        self.use_kivy_settings = True
        return Interface()

    def on_stop(self):
        self.root.stop_event.set()

    def build_config(self, config):

        # set up default values.
        # the relationships between each category
        # and each panel is defined in the settings file.

        config.setdefaults('worm info', {
            'strain': 'N2',
            'genotype': '',
            'wormsex': 'H',
            'wormstage': 'adult',
            'wormcomment': 'lay-off synchronization'
        })

        config.setdefaults('experiment settings', {
            'systemid': 'test',
            'paired_systemid': 'paired_test',
            'physical': 'agar',
            'local_exp_path': CURDIR,
            'remote_exp_path': '/Apps/wormscope_uploads/',
            'experimentlength': 120,
            'google_spreadsheet_id': GOOGLE_SPREADSHEET_ID,
            'rclone_remote_name': 'dropbox'
        })

        config.setdefaults('LED matrix', {
            'timelapse_options': 'None',
            'hc_image_frequency': 10,
            'ledcolor': '[255, 0, 0]',
            'matrixradius': 0,
            'ledx': 16,
            'ledy': 16
            })

        config.setdefaults('camera settings', {
            'fps': 30,
            'gain': 1.0,
            'resolution': '1920x1080',
            'video_length': 30,
            'inter_video_interval': 0
        })

        config.setdefaults('webstreaming', {
            'do_webstream': 0,
            'youtube_link': "rtmp://a.rtmp.youtube.com/live2/",
            'youtube_key': "xxxxxxxxxxxxxxxx"
        })

        config.setdefaults('pressure control', {
            'pressurepath': CURDIR
        })

        config.setdefaults('main image processing', {
            'image_processing_mode': 'None',
            'motion_with_feedback': 0,
            'sleep_prior': 10,
            'max_exposure': 30,
            'image_resolution': '640x480',
            'image_frequency': 15,
            'save_images': 0,
            'is_driving_system': 1,
            'check_dosage_interval': 360,
            'paired_systemid': 'test2'
        })

        config.setdefaults('image delta', {
            'delta_threshold': 4,
            'num_pixel_threshold': 2000
        })

        config.setdefaults('image thresholding', {
            'thresh_block_size': 61,
            'keep_border_data': 0,
            'image_threshold': 10,
            'min_area': 50,
            'max_area': 600,
            'dilation_size': 5,
            'xmin': 0,
            'xmax': 480,
            'ymin': 0,
            'ymax': 640
        })

    def build_settings(self, settings):
        settings.add_json_panel('Experiment Info', self.config,
                                data=expSettings_json)
        settings.add_json_panel('Imaging Setup', self.config,
                                data=imagingSettings_json)
        settings.add_json_panel('Pressure Control', self.config,
                                data=pressureSettings_json)
        settings.add_json_panel('Image Processing', self.config,
                                data=imageProcessingSettings_json)

    def on_config_change(self, config, section, key, value):
        # check key/values to make sure they make sense and update them to dropbox

        if key == 'systemid':
            # check that it's a recognized system id (found in 'keys' file)
            if value not in SYSTEM_IDS:
                Logger.info('App: System ID ' + key + ' not in recognized system IDs')
        if key == 'ledx' or key == 'ledy' or key == 'ledcolor' or key == 'matrixradius':
            self.root.set_config()

    def close_settings(self, settings=None):
        Logger.info('App: close settings')
        self.root.set_config()
        super(KivycamApp, self).close_settings(settings)


if __name__ == '__main__':
    KivycamApp().run()
