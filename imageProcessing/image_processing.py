import threading
import queue
import io
import time
from statistics import mean
import os
from os.path import join

import cv2
from PIL import Image
import numpy as np
from kivy.logger import Logger
import picamera
import picamera.array

from imageProcessing.CNN import CNN, tfliteCNN


def interpolate_all_points(points):
    interp_points = np.empty([0, 2])
    for i in range(0, points.shape[0]-1):
        # take 2 points at a time, find the distance between them
        new_points = interpolate_points(points[i:i+2, :])
        interp_points = np.concatenate((interp_points, new_points))
    # finally, make sure the loop is closed by taking the first and last points
    new_points = interpolate_points(points[::len(points)-1])
    interp_points = np.concatenate((interp_points, new_points))
    points = np.concatenate((points, interp_points))
    return points


def interpolate_points(points):
    norm = np.linalg.norm(points[0, :] - points[1, :])
    norm = int(norm)
    xvals = np.linspace(min(points[0, 0], points[1, 0]), max(points[0, 0], points[1, 0]), norm + 1)
    if points[1, 0] == points[0, 0]:
        yinterp = np.linspace(min(points[0, 1], points[1, 1]), max(points[0, 1], points[1, 1]), norm + 1)
    else:
        slope = (points[1, 1] - points[0, 1]) / (points[1, 0] - points[0, 0])
        yinterp = (xvals - points[0, 0]) * slope + points[0, 1]
    new_points = np.concatenate((np.reshape(xvals, (-1, 1)), np.reshape(yinterp, (-1, 1))), axis=1)
    return new_points


def get_mask_from_annotation(points, width, height):
    points = np.asarray(points)
    points = np.reshape(points, (-1, 2))
    points = interpolate_all_points(points)
    points = points.astype(int)
    mask_in = np.zeros((height + 2, width + 2), np.uint8)
    # add points from line to image (add one to each x and y!)
    mask_in_x = [element + 1 for element in points[:, 0]]
    mask_in_y = [element + 1 for element in points[:, 1]]
    mask_in[mask_in_y, mask_in_x] = 255
    kernel = np.ones((3, 3), np.uint8)
    mask_in = cv2.dilate(mask_in, kernel, iterations=1)
    # the seedpoint at (0,0) implies that the region of interest isn't at the edge of the image
    cv2.floodFill(mask_in, None, (0, 0), 255)
    # invert the mask
    mask_in = cv2.bitwise_not(mask_in)
    # check where the mask isn't zero
    y, x = np.nonzero(mask_in)
    # if there are too many points, kivy can't display it, so downsample
    if len(y) > 5001:
        idx = np.random.choice(np.arange(len(x)), 5000, replace=False)
        x = x[idx]
        y = y[idx]
    # reorganize points into the right format for kivy Point
    lawn_points = []
    for xel, yel in zip(x, y):
        lawn_points += [xel, yel]
    return lawn_points


def apply_mask(img, mask):
    img = cv2.bitwise_and(img, img, mask=mask)
    return img


def get_contour_areas(img, imaging_parameters):
    im_limx = img.shape[0] - 2
    im_limy = img.shape[1] - 2
    # currently copy pasta'd from Tierpsy Tracker
    mask = cv2.adaptiveThreshold(
        img,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        imaging_parameters['thresh_block_size'],
        -imaging_parameters['threshold_c'])
    # find the contour of the connected objects (much faster than labeled
    # images)
    contours, hierarchy = cv2.findContours(
        mask.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # find good contours: between max_area and min_area, and do not touch the
    # image border
    goodAreas = []
    for contour in contours:
        if not imaging_parameters['keep_border_data']:
            # eliminate blobs that touch a border
            keep = not np.any(contour == 1) and \
                   not np.any(contour[:, :, 0] == im_limy) \
                   and not np.any(contour[:, :, 1] == im_limx)
        else:
            keep = True

        if keep:
            area = cv2.contourArea(contour)
            if (area >= imaging_parameters['min_area']) and (area <= imaging_parameters['max_area']):
                goodAreas.append(area)
    return mean(goodAreas)


def delta_movement(im1, im2, frame_no, imaging_parameters):
    diff1 = cv2.subtract(im1, im2)
    diff1 = cv2.morphologyEx(diff1, cv2.MORPH_OPEN, imaging_parameters['strel'])

    diff2 = cv2.subtract(im2, im1)
    diff2 = cv2.morphologyEx(diff2, cv2.MORPH_OPEN, imaging_parameters['strel'])

    diff1 = diff1 > imaging_parameters['delta_threshold']
    diff2 = diff2 > imaging_parameters['delta_threshold']

    mvmnt = np.sum(diff1) + np.sum(diff2)

    if imaging_parameters['save_processed_images']:
        diff1.dtype = 'uint8'
        diff2.dtype = 'uint8'
        im_diff = cv2.add(diff1*255, diff2*255)
        im_diff = cv2.cvtColor(im_diff, cv2.COLOR_GRAY2RGB)
        fn = 'img' + str(frame_no) + '.png'
        fp2 = join(imaging_parameters['img_dir'], 'processed', fn)
        cv2.imwrite(fp2, im_diff)

    return mvmnt


class ProcessorPool:

    def __init__(self, **kwargs):
        self.done = False
        self.cur_image = kwargs['current_image']
        self.lock = threading.Lock()
        self.motion_list = kwargs['motion_list']
        self.motion_list_lock = kwargs['motion_list_lock']
        self.egg_count_list = kwargs['egg_list']
        self.egg_count_list_lock = kwargs['egg_list_lock']
        self.processor = None
        self.pool = None
        Logger.info('ProcessorPool: initialized')

    def write(self, image):
        pass

    def flush(self):
        pass

    def exit(self):
        if self.processor:
            with self.lock:
                self.pool.append(self.processor)
                self.processor = None
        # Now, empty the pool, joining each thread as we go
        while self.pool:
            with self.lock:
                try:
                    proc = self.pool.pop()
                except IndexError:
                    pass  # pool is empty
            proc.terminated = True
            proc.join()
        Logger.info('ProcessorPool: exiting')
        self.done = True


class ImageProcessorPool(ProcessorPool):
    def __init__(self, **kwargs):
        self.num_threads = kwargs.pop('num_threads')
        super(ImageProcessorPool, self).__init__(**kwargs)
        self.frame_queue = queue.Queue(maxsize=self.num_threads)
        self.pool = [ImageProcessor(self) for i in range(self.num_threads)]

    def write(self, image):
        if not self.done:
            with self.lock:
                if self.pool:
                    # if pool's not empty, grab a processor
                    self.processor = self.pool.pop()
                else:
                    # No processor's available, we'll have to skip
                    # this frame; you may want to print a warning
                    # here to see whether you hit this case
                    self.processor = None
                    Logger.info('ImageProcessorPool: no processor available')
            if self.processor:
                try:
                    self.processor.stream.write(image)
                    self.processor.im_event.set()
                except MemoryError:
                    Logger.debug('ImageProcessorPool: memory error whilst writing image to stream')

    def exit(self):
        # make sure frame queue is cleared out
        while not self.frame_queue.empty():
            self.frame_queue.get()
            self.frame_queue.task_done()
        self.frame_queue.join()
        if self.processor:
            with self.lock:
                self.pool.append(self.processor)
                self.processor = None
        # Now, empty the pool, joining each thread as we go
        while self.pool:
            with self.lock:
                try:
                    proc = self.pool.pop()
                except IndexError:
                    pass  # pool is empty
            proc.terminated = True
            proc.join()
        Logger.info('ImageProcessorPool: exiting')
        self.done = True


class VideoProcessorPool(ProcessorPool):
    def __init__(self, **kwargs):
        self.num_threads = kwargs.pop('num_threads')
        super(VideoProcessorPool, self).__init__(**kwargs)
        self.is_first_frame = True
        self.frame_count = 0
        self.pool = [VideoProcessor(self) for i in range(self.num_threads)]

    def write(self, image):
        if not self.done:
            if image.startswith(b'\xff\xd8'):
                with self.lock:
                    self.frame_count += 1
                    if self.pool:
                        # if pool's not empty, grab a processor
                        self.processor = self.pool.pop()
                        Logger.debug('VideoProcessorPool: processor grabbed')
                    else:
                        # No processor's available, we'll have to skip
                        # this frame; you may want to print a warning
                        # here to see whether you hit this case
                        self.processor = None
                        Logger.info('VideoProcessorPool: no processor available')
                if self.processor:
                    try:
                        self.processor.stream.write(image)
                        self.processor.im_event.set()
                        Logger.debug('VideoProcessorPool: im_event is set')
                    except MemoryError:
                        Logger.debug('VideoProcessorPool: memory error whilst writing image to stream')

    def flush(self):
        # When told to flush (this indicates end of recording), shut
        # down in an orderly fashion, add the current processor
        # back to the pool
        if self.processor:
            with self.lock:
                self.pool.append(self.processor)
                self.processor = None


class ImageProcessor(threading.Thread):
    def __init__(self, owner):
        super(ImageProcessor, self).__init__(name='im_processor')
        self.im_event = threading.Event()
        self.frame_event = threading.Event()
        self.terminated = False
        self.stream = io.BytesIO()
        self.owner = owner
        self.start()

    def run(self):
        img_parameters = self.owner.cur_image.imaging_parameters
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be added to the queue
            if self.im_event.wait(1):
                if self.frame_event.wait(1):
                    try:
                        t1 = time.time()

                        if len(self.stream.getvalue()) != (self.owner.cur_image.fwidth *
                                                           self.owner.cur_image.fheight * 3):
                            fwidth, fheight = self.owner.cur_image.raw_resolution((self.owner.cur_image.width,
                                                                                   self.owner.cur_image.height),
                                                                                  splitter=True)
                            if len(self.stream.getvalue()) != (fwidth * fheight * 3):
                                raise picamera.PiCameraValueError(
                                    'Incorrect buffer length for resolution %dx%d' % (self.owner.cur_image.width,
                                                                                      self.owner.cur_image.height))
                        # convert the image to a numpy array usable by opencv
                        im = np.frombuffer(self.stream.getvalue(), dtype=np.uint8). \
                            reshape((self.owner.cur_image.fheight, self.owner.cur_image.fwidth, 3))[
                             :self.owner.cur_image.height, :self.owner.cur_image.width, :]
                        Logger.debug('ImageProcessor: image converted')
                        self.frame_event.wait(timeout=5)
                        frame_no = self.owner.frame_queue.get()
                        Logger.info('ImageProcessor: Frame %s' % frame_no)
                        # if it's the first frame, we just convert to grayscale
                        if frame_no is 1:

                                im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                                if img_parameters['save_images']:
                                    fp = join(img_parameters['img_dir'], 'unprocessed', 'img1.png')
                                    cv2.imwrite(fp, im)

                                if self.owner.cur_image.image_processing_mode == 'neural net':
                                    # get worm location and set it
                                    with self.owner.cur_image.CNN.lock:
                                        worm_loc_x, worm_loc_y = self.owner.cur_image.CNN.get_worm_location(im, frame_no)
                                    self.owner.cur_image.set_worm_loc(worm_loc_x, worm_loc_y)

                                elif self.owner.cur_image.image_processing_mode == 'image delta':
                                    self.owner.cur_image.set_image(im)

                                time_elapsed = time.time() - t1
                                Logger.info(
                                    'ImageProcessor: First image processed, time elapsed is %s, frame no is %s'
                                    % (time_elapsed, frame_no))


                        # if it's past the first frame, convert to gray and calculate the movement delta between this
                        # and the previous image and send that info to the Update process via the motion_queue
                        else:
                                # convert new image to gray

                                im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                                if img_parameters['save_images']:
                                    fn = 'img' + str(frame_no) + '.png'
                                    fp = join(img_parameters['img_dir'], 'unprocessed', fn)
                                    cv2.imwrite(fp, im)

                                if self.owner.cur_image.image_processing_mode == 'image delta':
                                    im1 = self.owner.cur_image.im
                                    mvmnt = delta_movement(im1, im, frame_no, img_parameters)
                                    self.owner.cur_image.set_image(im)

                                    with self.owner.motion_list_lock:
                                        self.owner.motion_list.append(mvmnt)

                                elif self.owner.cur_image.image_processing_mode == 'neural net':
                                    if not self.owner.cur_image.nn_count_eggs:
                                        with self.owner.cur_image.CNN.lock:
                                            new_worm_loc_x, new_worm_loc_y = \
                                                self.owner.cur_image.CNN.get_worm_location(im, frame_no)

                                        old_worm_loc_x, old_worm_loc_y = self.owner.cur_image.get_last_worm_loc()
                                        # distance between the old and new box centers
                                        if new_worm_loc_y is not None and old_worm_loc_y is not None:
                                            mvmnt = np.sqrt(np.square(new_worm_loc_x - old_worm_loc_x) +
                                                            np.square(new_worm_loc_y - old_worm_loc_y))

                                            with self.owner.motion_list_lock:
                                                self.owner.motion_list.append(mvmnt)

                                        if new_worm_loc_y is not None:
                                            # set worm_loc in cur_image
                                            self.owner.cur_image.set_worm_loc(new_worm_loc_x, new_worm_loc_y)

                                    elif self.owner.cur_image.nn_count_eggs:
                                        with self.owner.cur_image.CNN.lock:
                                            num_eggs, new_worm_loc_x, new_worm_loc_y = \
                                                self.owner.cur_image.CNN.get_worm_location_and_count_eggs(im, frame_no)

                                        old_worm_loc_x, old_worm_loc_y = self.owner.cur_image.get_last_worm_loc()
                                        # distance between the old and new box centers
                                        if new_worm_loc_y is not None and old_worm_loc_y is not None:
                                            mvmnt = np.sqrt(np.square(new_worm_loc_x - old_worm_loc_x) +
                                                            np.square(new_worm_loc_y - old_worm_loc_y))

                                            with self.owner.motion_list_lock:
                                                self.owner.motion_list.append(mvmnt)
                                        if new_worm_loc_y is not None:
                                            # set worm_loc in cur_image
                                            self.owner.cur_image.set_worm_loc(new_worm_loc_x, new_worm_loc_y)

                                        with self.owner.egg_count_list_lock:
                                            self.owner.egg_count_list.append(num_eggs)

                                time_elapsed = time.time() - t1

                                Logger.info('ImageProcessor: image processed, time elapsed is %s, frame no is %s'
                                            % (time_elapsed, frame_no))

                        # reset frame event to False
                        self.owner.frame_queue.task_done()

                    finally:
                        self.stream.seek(0)
                        self.stream.truncate()
                        # Reset the events
                        self.im_event.clear()
                        self.frame_event.clear()
                        Logger.debug('ImageProcessor: Returning processor to pool')
                        # Return ourselves to the available pool
                        with self.owner.lock:
                            self.owner.pool.append(self)


class VideoProcessor(threading.Thread):
    def __init__(self, owner):
        super(VideoProcessor, self).__init__(name='vid_processor')
        self.im_event = threading.Event()
        self.terminated = False
        self.stream = io.BytesIO()
        self.owner = owner
        self.start()

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be added to the queue
            if self.im_event.wait(1):
                Logger.debug('VideoProcessor: frame arrived')
                try:
                    t1 = time.time()
                    self.stream.seek(0)
                    im = Image.open(self.stream).convert('RGB').resize(
                                    (self.owner.cur_image.CNN.input_width,
                                     self.owner.cur_image.CNN.input_height), Image.ANTIALIAS)
                    Logger.debug('VideoProcessor: frame converted')

                    # no need to save the video separately, as it's already being saved.

                    with self.owner.cur_image.CNN.lock:
                        new_worm_loc_x, new_worm_loc_y = \
                            self.owner.cur_image.CNN.get_worm_location(im, self.owner.frame_count)

                    old_worm_loc_x, old_worm_loc_y = self.owner.cur_image.get_last_worm_loc()
                    # distance between the old and new box centers
                    if new_worm_loc_y is not None and old_worm_loc_y is not None:
                        mvmnt = np.sqrt(np.square(new_worm_loc_x - old_worm_loc_x) +
                                        np.square(new_worm_loc_y - old_worm_loc_y))

                        with self.owner.motion_list_lock:
                            self.owner.motion_list.append(mvmnt)

                    if new_worm_loc_y is not None:
                        # set worm_loc in cur_image
                        self.owner.cur_image.set_worm_loc(new_worm_loc_x, new_worm_loc_y)

                    time_elapsed = time.time() - t1

                    Logger.info('VideoProcessor: image processed, time elapsed is %s, frame no is %s'
                                % (time_elapsed, self.owner.frame_count))

                finally:
                    self.stream.seek(0)
                    self.stream.truncate()
                    # Reset the events
                    self.im_event.clear()
                    Logger.debug('VideoProcessor: Returning processor to pool')
                    # Return ourselves to the available pool
                    with self.owner.lock:
                        self.owner.pool.append(self)


class CurrentImage:
    def __init__(self, imaging_parameters):
        self.im = None
        self.imaging_parameters = imaging_parameters
        self.image_processing_mode = imaging_parameters['image_processing_mode']
        self.imaging_parameters['strel'] = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
        self.lock = threading.Lock()
        self.width, self.height = self.imaging_parameters['image_resolution']
        self.fwidth, self.fheight = self.raw_resolution((self.width, self.height))
        if self.image_processing_mode == 'neural net':
            # start without a worm location
            self.worm_loc = (None, None)
            self.nn_count_eggs = imaging_parameters['nn_count_eggs']
            self.cwd = os.getcwd()
            # load the frozen inference graph and label map, and set up general parameters
            if self.imaging_parameters['neural_net_type'] == 'Faster R-CNN':
                self.CNN = CNN(self.imaging_parameters['save_processed_images'], self.imaging_parameters['img_dir'],
                            (self.fwidth, self.fheight))
            elif self.imaging_parameters['neural_net_type'] == 'Mobilenet':
                self.CNN = tfliteCNN(save_worm_loc=self.imaging_parameters['save_processed_images'],
                                     img_dir=self.imaging_parameters['img_dir'],
                                     label_path=join(self.cwd, 'neural_net/label_map.txt'),
                                     model_path=join(self.cwd, 'neural_net/model.tflite'),
                                     video_resolution=(self.fwidth, self.fheight))
            elif self.imaging_parameters['neural_net_type'] == 'Mobilenet with Edge TPU':
                self.CNN = tfliteCNN(save_worm_loc=self.imaging_parameters['save_processed_images'],
                                     img_dir=self.imaging_parameters['img_dir'],
                                     label_path=join(self.cwd, 'neural_net/label_map.txt'),
                                     model_path=join(self.cwd, 'neural_net/edgetpu_model.tflite'),
                                     on_edge_tpu=True,
                                     video_resolution=(self.fwidth, self.fheight))

        Logger.debug('CurrentImage: initialized')

    def raw_resolution(self, resolution, splitter=False):
        """
        This is from the picamera source code
        Round a (width, height) tuple up to the nearest multiple of 32 horizontally
        and 16 vertically (as this is what the Pi's camera module does for
        unencoded output).
        """
        width, height = resolution
        if splitter:
            fwidth = (width + 15) & ~15
        else:
            fwidth = (width + 31) & ~31
        fheight = (height + 15) & ~15
        return fwidth, fheight

    def set_image(self, im):
        with self.lock:
            self.im = im
            Logger.debug('CurrentImage: updated')

    def set_worm_loc(self, worm_loc_x, worm_loc_y):
        with self.lock:
            self.worm_loc = (worm_loc_x, worm_loc_y)
            Logger.debug('CurrentImage: worm location updated')

    def get_last_worm_loc(self):
        with self.lock:
            return self.worm_loc

