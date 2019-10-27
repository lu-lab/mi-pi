import cv2
import numpy as np
import threading
import multiprocessing
import queue
import io
from kivy.logger import Logger
import time

from statistics import mean
from os.path import join
from imageProcessing.CNN import CNN

import picamera
import picamera.array


def get_image_mask(img, imaging_parameters):

    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
    goodIndex = []
    for ii, contour in enumerate(contours):
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
                goodIndex.append(ii)

    # typically there are more bad contours therefore it is cheaper to draw
    # only the valid contours
    mask = np.zeros(img.shape, dtype=img.dtype)
    for ii in goodIndex:
        cv2.drawContours(mask, contours, ii, 1, cv2.FILLED)

    # drawContours left an extra line if the blob touches the border. It is
    # necessary to remove it
    mask[0, :] = 0
    mask[:, 0] = 0
    mask[-1, :] = 0
    mask[:, -1] = 0

    # dilate the elements to increase the ROI, in case we are missing
    # something important
    struct_element = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (imaging_parameters['dilation_size'], imaging_parameters['dilation_size']))
    mask = cv2.dilate(mask, struct_element, iterations=3)

    return mask


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

    def __init__(self, num_threads, cur_image,
                 motion_list, motion_list_lock,
                 egg_count_list, egg_count_list_lock):
        self.done = False
        self.cur_image = cur_image
        self.lock = threading.Lock()
        self.motion_list = motion_list
        self.motion_list_lock = motion_list_lock
        self.egg_count_list = egg_count_list
        self.egg_count_list_lock = egg_count_list_lock
        self.frame_queue = queue.Queue(maxsize=num_threads)
        self.processor = None
        self.pool = [ImageProcessor(self) for i in range(num_threads)]
        Logger.info('ProcessorPool: initialized')

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
                    Logger.info('ProcessorPool: no processor available')
            if self.processor:
                try:
                    self.processor.stream.write(image)
                    self.processor.im_event.set()
                except MemoryError:
                    Logger.debug('ProcessorPool: memory error whilst writing image to stream')

    def flush(self):
        pass

    def exit(self):
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
        Logger.info('ProcessorPool: exiting')
        self.done = True


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
            # load the frozen inference graph and label map, and set up general parameters
            self.CNN = CNN(self.imaging_parameters['save_processed_images'], self.imaging_parameters['img_dir'],
                           (self.fwidth, self.fheight))

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

