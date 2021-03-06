import time
from datetime import datetime
from os.path import join
from kivy.logger import Logger
import configparser
import subprocess
import threading

import psutil
import cv2
import numpy as np
import math

from imageProcessing.image_processing import ProcessorPool, CurrentImage, delta_movement

try:
    import picamera
    import picamera.array
except ImportError:
    print('Probably attempting to run on a non-RPi system or without picamera modules')
    raise


def build_stream_command(fps, youtube_link, youtube_key):
    stream_cmd = 'ffmpeg -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -f h264 -r %s -i - -c:v copy -c:a aac -ab 128k -strict experimental -f flv -r %s %s%s ' % (fps, fps, youtube_link, youtube_key)
    return stream_cmd


class CameraSupport(threading.Thread):

    def __init__(self, camera, config_file, image_processing_params,
                 timelapse_option, ledMatrix, stop_exp_event,
                 stop_cam_event, video_length, end_time, motion_list,
                 motion_list_lock, egg_count_list, egg_count_list_lock):
        super(CameraSupport, self).__init__()
        config = configparser.ConfigParser()
        config.read(config_file)
        self.stop_exp_event = stop_exp_event
        self.stop_cam_event = stop_cam_event
        self.motion_list = motion_list
        self.motion_list_lock = motion_list_lock
        self.egg_count_list = egg_count_list
        self.egg_count_list_lock = egg_count_list_lock
        self.end_time = end_time
        self.ledMatrix = ledMatrix

        self.fps = config['camera settings']['fps']
        self.resolution = config['camera settings']['resolution']
        self.gain = config['camera settings']['gain']
        self.inter_video_interval = int(config['camera settings']['inter_video_interval'])

        self.webstream = bool(int(config['webstreaming']['do_webstream']))
        self.youtube_link = config['webstreaming']['youtube_link']
        self.youtube_key = config['webstreaming']['youtube_key']

        self.image_processing_params = image_processing_params
        self.image_processing_mode = config['main image processing']['image_processing_mode']
        if self.image_processing_mode == 'neural net':
            # reduce size of image to try to save memory - since tensorflow will resize anyway
            width, height = self.image_processing_params['image_resolution']
            new_width = 1024
            new_height = int((new_width / width) * height)
            self.image_processing_params['image_resolution'] = new_width, new_height
        self.image_processing_params['nn_count_eggs'] = bool(int(config['neural net']['nn_count_eggs']))
        self.img_pool = None

        self.image_frequency = int(config['main image processing']['image_frequency'])
        self.hc_image_frequency = int(config['LED matrix']['hc_image_frequency'])
        self.timelapse_option = timelapse_option

        self.save_dir = config['experiment settings']['local_exp_path']
        self.video_save_dir = join(self.save_dir, 'videos')
        self.image_processing_params['img_dir'] = join(self.save_dir, 'images')
        self.video_length = video_length

        Logger.info('webstream is %s, image processing mode is %s' % (self.webstream, self.image_processing_mode))
        if camera is not None:
            camera.close()

        # set resolution and fps
        self.camera = picamera.PiCamera(resolution=self.resolution)
        self.camera.framerate = int(float(self.fps))

        # determine the difference in images taken under blue LEDs on vs. off.
        self.image_processing_params['strel'] = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
        self.mvmnt, self.led_difference = self.calibrate_brightness()
        if self.led_difference > self.mvmnt:
            self.max_difference = self.led_difference
        else:
            width, height = self.camera.resolution
            self.max_difference = (width * height) / 16

        Logger.info('Camera: video path %s' % self.video_save_dir)
        Logger.info('Camera: images path %s' % self.image_processing_params['img_dir'])
        Logger.info('Camera: local init success')

    def run(self):

        if self.timelapse_option == 'None':
            if not self.webstream and self.image_processing_mode == 'None':
                self.video_only()

            elif self.webstream and self.image_processing_mode == 'None':
                self.video_and_webstream()

            elif self.image_processing_mode != 'None' and not self.webstream:
                self.video_and_motion()

            elif self.webstream and self.image_processing_mode != 'None':
                self.video_and_motion_and_webstream()

        elif self.timelapse_option == 'linescan':
            self.linescan_timelapse()

        elif self.timelapse_option == 'brightfield' or self.timelapse_option == 'darkfield':
            self.timelapse()

        return

    def video_only(self):
        Logger.info('Camera: Video capture only')
        # record a sequence of videos until the end of the experiment
        with picamera.PiCameraCircularIO(self.camera, seconds=self.video_length, splitter_port=2) as stream:
            self.camera.start_recording(stream, format='h264', splitter_port=2)
            try:
                start_time = time.time()
                Logger.info('Camera: recording started, start time is: %s' % start_time)
                while not self.is_exp_done() and not self.stop_cam_event.is_set():
                    self.camera.wait_recording(self.video_length, splitter_port=2)
                    timestr = time.strftime("%Y%m%d_%H%M%S")
                    videofile = "VID_{}.h264".format(timestr)
                    videopath = join(self.video_save_dir, videofile)
                    stream.copy_to(videopath)
                    stream.clear()
                    time.sleep(self.inter_video_interval)
            except picamera.PiCameraError:
                # if for whatever reason the picamera has some sort of error, close the camera and restart the function!
                Logger.info('Camera: PiCamera error, re-starting camera')
                if self.camera is not None:
                    self.camera.close()
                # set resolution and fps
                self.camera = picamera.PiCamera(resolution=self.resolution)
                self.camera.framerate = int(float(self.fps))
                self.video_only()
            finally:
                # wait a few seconds to make sure everything is wrapped up
                time.sleep(5)
                # stop recording gracefully
                try:
                    self.camera.stop_recording(splitter_port=2)
                except picamera.PiCameraNotRecording:
                    # the splitter port has already stopped recording
                    pass
                Logger.info('Camera: recording stopped')
                self.stop_exp_event.set()

    def video_and_webstream(self):
        Logger.info('Camera: Video and youtube livestream')
        stream_cmd = build_stream_command(self.fps, self.youtube_link, self.youtube_key)
        stream_pipe = subprocess.Popen(stream_cmd, shell=True, stdin=subprocess.PIPE)
        with picamera.PiCameraCircularIO(self.camera, seconds=self.video_length, splitter_port=2) as stream:
            self.camera.start_recording(stream, format='h264', splitter_port=2)
            self.camera.start_recording(stream_pipe.stdin, format='h264', bitrate=2000000, splitter_port=3)
            try:
                start_time = time.time()
                Logger.info('Camera: recording started, start time is: %s' % start_time)
                while not self.is_exp_done() and not self.stop_cam_event.is_set():
                    self.camera.wait_recording(self.video_length, splitter_port=2)
                    # if there's an issue with the stream and it closes,
                    # just ignore it and continue recording to disk
                    try:
                        self.camera.wait_recording(self.video_length, splitter_port=3)
                    except picamera.PiCameraNotRecording:
                        pass
                    timestr = time.strftime("%Y%m%d_%H%M%S")
                    videofile = "VID_{}.h264".format(timestr)
                    videopath = join(self.video_save_dir, videofile)
                    stream.copy_to(videopath)
                    stream.clear()
                    time.sleep(self.inter_video_interval)

            except BrokenPipeError:
                Logger.warning('Streaming: Your youtube link or youtube key is likely invalid')
                self.camera.stop_recording(splitter_port=3)
            except picamera.PiCameraError:
                # if for whatever reason the picamera has some sort of error, close the camera and restart the function!
                Logger.info('Camera: PiCamera error, re-starting camera')
                if self.camera is not None:
                    self.camera.close()
                # set resolution and fps
                self.camera = picamera.PiCamera(resolution=self.resolution)
                self.camera.framerate = int(float(self.fps))
                self.video_and_webstream()
            finally:
                # wait a few seconds to make sure everything is wrapped up
                time.sleep(5)
                # stop recording gracefully
                try:
                    self.camera.stop_recording(splitter_port=2)
                    self.camera.stop_recording(splitter_port=3)
                except picamera.PiCameraNotRecording:
                    # the camera is already closed, and that's fine
                    pass
                stream_pipe.stdin.close()
                try:
                    stream_pipe.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    stream_pipe.kill()
                Logger.info('Camera: recording stopped')
                self.stop_exp_event.set()

    def video_and_motion(self):
        Logger.info('Camera: video and local motion detection')
        cur_image = CurrentImage(self.image_processing_params)
        self.img_pool = ProcessorPool(3, cur_image, self.motion_list, self.motion_list_lock,
                                      self.egg_count_list, self.egg_count_list_lock)
        with picamera.PiCameraCircularIO(self.camera, seconds=self.video_length, splitter_port=2) as stream:
            self.camera.start_recording(stream, format='h264', splitter_port=2)
            try:
                start_time = time.time()
                Logger.info('Camera: recording started, start time is: %s' % start_time)
                self.camera.capture(self.img_pool, format='bgr', splitter_port=3,
                                    resize=self.image_processing_params['image_resolution'],
                                    use_video_port=True)
                Logger.info('Camera: capture at time %s' % time.strftime("%Y%m%d_%H%M%S"))
                img_counter = 1
                if self.img_pool.processor is not None:
                    self.img_pool.frame_queue.put(img_counter)
                    Logger.debug('Camera: img_counter in frame queue')
                    self.img_pool.processor.frame_event.set()
                    Logger.debug('Camera: frame_event set')
                t_image = 0
                while not self.is_exp_done() and not self.stop_cam_event.is_set():
                    Logger.debug('Camera: video recording started')
                    t_video = 0
                    while t_video < self.video_length:
                        self.camera.wait_recording(1, splitter_port=2)
                        t_video += 1
                        t_image += 1
                        if t_image == self.image_frequency:
                            self.camera.capture(self.img_pool, format='bgr', splitter_port=3,
                                                resize=self.image_processing_params['image_resolution'],
                                                use_video_port=True)
                            Logger.info('Camera: capture while collecting video at time %s' % time.time())
                            img_counter += 1
                            if self.img_pool.processor is not None:
                                self.img_pool.frame_queue.put(img_counter)
                                Logger.debug('Camera: img_counter in frame queue')
                                self.img_pool.processor.frame_event.set()
                                Logger.debug('Camera: frame_event set')
                            vmem = psutil.virtual_memory()
                            Logger.debug('Memory usage is %s' % vmem.percent)
                            t_image = 0
                    timestr = time.strftime("%Y%m%d_%H%M%S")
                    videofile = "VID_{}.h264".format(timestr)
                    videopath = join(self.video_save_dir, videofile)
                    stream.copy_to(videopath)
                    stream.clear()
                    Logger.debug('Camera: video %s collected' % videopath)
                    t_inter_video = 0
                    if self.inter_video_interval > 0:
                        Logger.debug('Camera: start inter-video interval')
                        while t_inter_video < self.inter_video_interval:
                            time.sleep(1)
                            t_image += 1
                            t_inter_video += 1
                            if t_image == self.image_frequency:
                                self.camera.capture(self.img_pool, format='bgr', splitter_port=3,
                                                    resize=self.image_processing_params['image_resolution'],
                                                    use_video_port=True)
                                Logger.info('Camera: capture during inter-video interval at time %s' % time.time())
                                img_counter += 1
                                if self.img_pool.processor is not None:
                                    self.img_pool.frame_queue.put(img_counter)
                                    # Logger.debug('Camera: img_counter in frame_queue')
                                    self.img_pool.processor.frame_event.set()
                                    # Logger.debug('Camera: frame_event set')
                                vmem = psutil.virtual_memory()
                                Logger.debug('Memory usage is %s' % vmem.percent)
                                t_image = 0
                        Logger.debug('Camera: end inter-video interval')

            except picamera.PiCameraError:
                # if for whatever reason the picamera isn't recording, restart the function!
                Logger.info('Camera: PiCamera error, re-starting camera')
                if self.camera is not None:
                    self.camera.close()
                # set resolution and fps
                self.camera = picamera.PiCamera(resolution=self.resolution)
                self.camera.framerate = int(float(self.fps))
                self.video_and_motion()
            finally:
               # wait a few seconds to make sure all image processing is wrapped up
                time.sleep(5)
                # stop recording gracefully
                try:
                    self.camera.stop_recording(splitter_port=2)
                except picamera.PiCameraNotRecording:
                    # the splitter port has already stopped recording
                    pass
                Logger.info('Camera: recording stopped')
                self.img_pool.exit()
                self.stop_exp_event.set()

    def video_and_motion_and_webstream(self):
        Logger.info('Camera: video, youtube live stream, and local motion detection')
        stream_cmd = build_stream_command(self.fps, self.youtube_link, self.youtube_key)
        stream_pipe = subprocess.Popen(stream_cmd, shell=True, stdin=subprocess.PIPE)
        cur_image = CurrentImage(self.image_processing_params)
        self.img_pool = ProcessorPool(3, cur_image, self.motion_list, self.motion_list_lock, self.egg_count_list, self.egg_count_list_lock)
        with picamera.PiCameraCircularIO(self.camera, seconds=self.video_length, splitter_port=2) as stream:
            self.camera.start_recording(stream, format='h264', splitter_port=2)
            self.camera.start_recording(stream_pipe.stdin, format='h264', bitrate=2000000, splitter_port=3)
            try:
                start_time = time.time()
                Logger.info('Camera: recording started, start time is: %s' % start_time)
                self.camera.capture(self.img_pool, format='bgr', splitter_port=0,
                                    resize=self.image_processing_params['image_resolution'],
                                    use_video_port=True)
                img_counter = 1
                if self.img_pool.processor is not None:
                    self.img_pool.frame_queue.put(img_counter)
                    self.img_pool.processor.frame_event.set()
                t_image = 0
                while not self.is_exp_done() and not self.stop_cam_event.is_set():
                    t_video = 0
                    while t_video < self.video_length:
                        self.camera.wait_recording(1, splitter_port=2)
                        try:
                            self.camera.wait_recording(1, splitter_port=3)
                        except picamera.PiCameraNotRecording:
                            pass
                        if t_image == self.image_frequency:
                            self.camera.capture(self.img_pool, format='bgr', splitter_port=0,
                                                resize=self.image_processing_params['image_resolution'],
                                                use_video_port=True)
                            img_counter += 1
                            if self.img_pool.processor is not None:
                                self.img_pool.frame_queue.put(img_counter)
                                self.img_pool.processor.frame_event.set()
                            t_image = 0
                        t_video += 1
                        t_image += 1
                    timestr = time.strftime("%Y%m%d_%H%M%S")
                    videofile = "VID_{}.h264".format(timestr)
                    videopath = join(self.video_save_dir, videofile)
                    stream.copy_to(videopath)
                    stream.clear()
                    t_inter_video = 0
                    if self.inter_video_interval > 0:
                        while t_inter_video < self.inter_video_interval:
                            time.sleep(1)
                            t_image += 1
                            t_inter_video += 1
                            if t_image == self.image_frequency:
                                self.camera.capture(self.img_pool, format='bgr', splitter_port=3,
                                                    resize=self.image_processing_params['image_resolution'],
                                                    use_video_port=True)
                                Logger.info('Camera: capture during inter-video interval at time %s' % time.time())
                                img_counter += 1
                                if self.img_pool.processor is not None:
                                    self.img_pool.frame_queue.put(img_counter)
                                    self.img_pool.processor.frame_event.set()
                                vmem = psutil.virtual_memory()
                                Logger.debug('Memory usage is %s' % vmem.percent)
                                t_image = 0

            except BrokenPipeError:
                Logger.warning('Streaming: Your youtube link or youtube key is likely invalid')
                self.camera.stop_recording(splitter_port=3)
            except picamera.PiCameraError as err:
                # if for whatever reason the picamera isn't recording, restart the function!
                Logger.info('Camera: PiCamera error, re-starting camera. Error is %s' % err)
                if self.camera is not None:
                    self.camera.close()
                # set resolution and fps
                self.camera = picamera.PiCamera(resolution=self.resolution)
                self.camera.framerate = int(float(self.fps))
                self.video_and_motion_and_webstream()
            finally:
                # wait a few seconds to make sure all image processing is wrapped up
                time.sleep(5)
                # stop recording gracefully
                try:
                    self.camera.stop_recording(splitter_port=2)
                    self.camera.stop_recording(splitter_port=3)
                except picamera.PiCameraNotRecording:
                    # the splitter port has already stopped recording
                    pass
                Logger.info('Camera: recording stopped')
                self.img_pool.exit()
                stream_pipe.stdin.close()
                try:
                    stream_pipe.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    stream_pipe.kill()
                self.stop_exp_event.set()

    def calibrate_brightness(self):
        # figure out the size of the numpy matrix to capture to
        # width and height must both be divisible by 16
        (width, height) = self.camera.resolution
        im_width = math.ceil(width / 16) * 16
        im_height = math.ceil(height / 16) * 16

        # make sure blue LEDs are off, take an image
        self.ledMatrix.send_command([{'matrix_mode': 'opto', 'is_on': str(0)}])
        time.sleep(1)
        im1 = np.empty((im_height, im_width, 3), dtype=np.uint8)
        self.camera.capture(im1, format='bgr', splitter_port=3, use_video_port=True)
        # now resize the image again
        im1 = im1[:height, :width, :]
        im1 = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)

        # take another image with the blue LEDs off
        time.sleep(1)
        im2 = np.empty((im_height, im_width, 3), dtype=np.uint8)
        self.camera.capture(im2, format='bgr', splitter_port=3, use_video_port=True)
        # now resize the image again
        im2 = im2[:height, :width, :]
        im2 = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)

        # make sure blue LEDs are on, take an image
        self.ledMatrix.send_command([{'matrix_mode': 'opto', 'is_on': str(1)}])
        time.sleep(1)
        im3 = np.empty((im_height, im_width, 3), dtype=np.uint8)
        self.camera.capture(im3, format='bgr', splitter_port=3, use_video_port=True)
        im3 = im3[:height, :width, :]
        im3 = cv2.cvtColor(im3, cv2.COLOR_BGR2GRAY)

        # turn the blue light back off.
        self.ledMatrix.send_command([{'matrix_mode': 'opto', 'is_on': str(0)}])

        imgfile1 = join(self.image_processing_params['img_dir'], "calibrate_1.png")
        cv2.imwrite(imgfile1, im1)
        imgfile2 = join(self.image_processing_params['img_dir'], "calibrate_2.png")
        cv2.imwrite(imgfile2, im2)
        imgfile3 = join(self.image_processing_params['img_dir'], "calibrate_3.png")
        cv2.imwrite(imgfile3, im3)

        self.width, self.height = self.image_processing_params['image_resolution']
        mvmnt = delta_movement(im1, im2, 0, self.image_processing_params)
        LED_difference = delta_movement(im2, im3, 0, self.image_processing_params)
        Logger.info('Camera: movement is %s, LED difference is %s' % (mvmnt, LED_difference))
        return mvmnt, LED_difference

    def linescan_timelapse(self):
        ymax = self.ledMatrix.center_y + self.ledMatrix.radius
        ymin = self.ledMatrix.center_y - self.ledMatrix.radius
        Logger.debug('Camera: linescan ymin is %s, linescan ymax is %s' % (str(ymin), str(ymax)))
        self.ledMatrix.linescan_int = ymax
        self.ledMatrix.send_command([{'matrix_mode': 'linescan_bright'}])
        time.sleep(2)
        # set up for consistent imaging
        # 400 for dark, 100 for bright
        self.camera.iso = 100
        # Wait for the automatic gain control to settle
        time.sleep(2)
        # Now fix the values
        self.camera.shutter_speed = self.camera.exposure_speed
        self.camera.exposure_mode = 'off'
        g = self.camera.awb_gains
        self.camera.awb_mode = 'off'
        self.camera.awb_gains = g

        counter = 1
        while not self.is_exp_done():
            for i in range(ymin, ymax+1):
                Logger.debug('Camera: linescan int is %s' % i)
                self.ledMatrix.linescan_int = i
                self.ledMatrix.send_command([{'matrix_mode': 'linescan_bright'}])
                fn = str(counter) + '_' + str(i)
                imgfile = join(self.image_processing_params['img_dir'], "IMG_{}.png".format(fn))
                time.sleep(self.hc_image_frequency)
                self.camera.capture(imgfile)
            counter += 1
        # send the stop signal to the rest of the app
        self.stop_exp_event.set()

    def timelapse(self):
        self.ledMatrix.send_command([{'matrix_mode': self.timelapse_option}])

        time.sleep(2)
        # set up for consistent imaging
        # 400 for dark, 100 for bright
        self.camera.iso = 100
        # Wait for the automatic gain control to settle
        time.sleep(2)
        # Now fix the values
        self.camera.shutter_speed = self.camera.exposure_speed
        self.camera.exposure_mode = 'off'
        g = self.camera.awb_gains
        self.camera.awb_mode = 'off'
        self.camera.awb_gains = g

        counter = 1
        while not self.is_exp_done():
            fn = str(counter)
            imgfile = join(self.image_processing_params['img_dir'], "IMG_{}.png".format(fn))
            time.sleep(self.hc_image_frequency)
            self.camera.capture(imgfile)
            counter += 1

        self.stop_exp_event.set()

    def is_exp_done(self):
        cur_time = datetime.now()
        Logger.debug('Camera: current time is %s' % cur_time.strftime("%H:%M:%S %B %d, %Y"))
        return cur_time > self.end_time
