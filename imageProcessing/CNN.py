import threading
import os
from os.path import join, exists

import cv2
import h5py
import numpy as np
from kivy.logger import Logger

from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util

import tensorflow as tf

class CNN:
    ''' The CNN class loads a frozen tensorflow inference graph for object detection. The internal '_run' method runs
    the actual detection, while the outward facing 'get_worm_location' method will specifically find the center of the
     bounding-box for the highest-scoring worm object (class 1 in the provided frozen inference graph). '''

    def __init__(self, save_processed_images, img_dir, img_dims):
        self.lock = threading.Lock()
        self.box_file_lock = threading.Lock()
        self.save_processed_images = save_processed_images
        self.img_dir = img_dir
        if self.save_processed_images:
            self.h5_file = join(self.img_dir, 'processed', 'data.h5')
        self.width, self.height = img_dims
        self.cwd = os.getcwd()
        self5.graph, self.sess, self.category_index = self.load_graph()
        Logger.info('CNN: tensorflow model loaded')

    def load_graph(self):

        detection_graph = tf.Graph()
        with detection_graph.as_default():
            od_graph_def = tf.compat.v1.GraphDef()
            with tf.io.gfile.GFile(join(self.cwd, 'neural_net/frozen_inference_graph.pb'), 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

        # Load label map
        label_map = label_map_util.load_labelmap(join(self.cwd, 'neural_net/label_map.pbtxt'))
        categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=2,
                                                                    use_display_name=True)
        category_index = label_map_util.create_category_index(categories)

        # create a session
        sess = tf.compat.v1.Session(graph=detection_graph)

        return detection_graph, sess, category_index

    def _run(self, expanded_image):

        with self.graph.as_default():
            image_tensor = self.graph.get_tensor_by_name('image_tensor:0')
            boxes = self.graph.get_tensor_by_name('detection_boxes:0')
            scores = self.graph.get_tensor_by_name('detection_scores:0')
            classes = self.graph.get_tensor_by_name('detection_classes:0')
            num_detections = self.graph.get_tensor_by_name('num_detections:0')

            # Actual detection.
            (boxes, scores, classes, num_detections) = self.sess.run(
                [boxes, scores, classes, num_detections],
                feed_dict={image_tensor: expanded_image})

            classes = np.squeeze(classes).astype(np.int32)
            boxes = np.squeeze(boxes)
            scores = np.squeeze(scores)
            return classes, boxes, scores

    def _prep_image(self, image):
        # transform back to color from grayscale
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        # change color order from BGR to RGB
        image = image[:, :, [2, 1, 0]]
        return image

    def _screen_results(self, target_class, min_score, classes, boxes, scores):
        # screen out classes that are not 1 (worm class) and scores > .8
        idx = (classes == target_class) & (scores >= min_score)
        boxes = boxes[idx]
        scores = scores[idx]
        classes = classes[idx]
        num_results = len(boxes)

        return num_results, classes, boxes, scores

    def _get_top_result(self, num_results, classes, boxes, scores):
        # default to none
        top_box = None
        top_score = None
        top_class = None
        # if more than one worm, take the one with the highest score
        if num_results > 1:
            # scores are always ordered from highest to lowest, so...
            top_box = np.squeeze(boxes[0])
            top_score = np.squeeze(scores[0])
            top_class = np.squeeze(classes[0])
        # if one worm, get it's coordinates
        elif num_results == 1:
            top_box = np.squeeze(boxes)
            top_score = np.squeeze(scores)
            top_class = np.squeeze(classes)

        return top_class, top_box, top_score

    def _get_box_center(self, box_coords):
        ymin, xmin, ymax, xmax = box_coords
        (left, right, top, bottom) = (xmin*self.width, xmax*self.width,
                                      ymin*self.height, ymax*self.height)
        center_x = ((right - left)/2) + left
        center_y = ((bottom - top)/2) + top
        return center_x, center_y

    def _label_image(self, image, box, score, class_idx=1):
        ymin, xmin, ymax, xmax = box
        class_label = self.category_index[class_idx]['name']
        display_str = '{}: {}%'.format(class_label, int(100*score))
        vis_util.draw_bounding_box_on_image_array(
            image,
            ymin,
            xmin,
            ymax,
            xmax,
            color='aquamarine',
            thickness=8,
            display_str_list=[display_str],
            use_normalized_coordinates=True)
        return image

    def get_worm_location(self, image, frame_no):
        # default to no center x or y position
        worm_center_x = None
        worm_center_y = None
        image = self._prep_image(image)
        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        expanded_image = np.expand_dims(image, axis=0)
        try:
            classes, boxes, scores = self._run(expanded_image)
            target_class = 1
            min_score = 0.8
            num_worms, worm_classes, worm_boxes, worm_scores = self._screen_results(target_class, min_score,
                                                                                    classes, boxes, scores)
            worm_class, worm_box, worm_score = self._get_top_result(num_worms, worm_classes, worm_boxes, worm_scores)

            if self.save_processed_images:
                if worm_box is not None:
                    with self.box_file_lock:
                        if exists(self.h5_file):
                            with h5py.File(self.h5_file, 'a') as hf:
                                frame_boxes_name = 'worm_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=worm_boxes)
                                frame_scores_name = 'worm_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=worm_scores)
                        else:
                            with h5py.File(self.h5_file, 'w') as hf:
                                frame_boxes_name = 'worm_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=worm_boxes)
                                frame_scores_name = 'worm_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=worm_scores)

            if worm_box is not None:
                worm_center_x, worm_center_y = self._get_box_center(worm_box)

        except tf.compat.v1.errors.ResourceExhaustedError:
            # just return the center point as None, None
            pass

        return worm_center_x, worm_center_y

    def count_eggs(self, image, frame_no):
        num_eggs = None
        # default to no center x or y positions
        image = self._prep_image(image)
        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        expanded_image = np.expand_dims(image, axis=0)
        try:

            classes, boxes, scores = self._run(expanded_image)
            target_class = 2
            min_score = 0.8
            num_eggs, egg_classes, egg_boxes, egg_scores = self._screen_results(target_class, min_score, classes, boxes, scores)
            if self.save_processed_images:
                if egg_boxes is not None:
                    with self.box_file_lock:
                        if exists(self.h5_file):
                            with h5py.File(self.h5_file, 'a') as hf:
                                frame_boxes_name = 'egg_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=egg_boxes)
                                frame_scores_name = 'egg_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=egg_scores)
                        else:
                            with h5py.File(self.h5_file, 'w') as hf:
                                frame_boxes_name = 'egg_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=egg_boxes)
                                frame_scores_name = 'egg_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=egg_scores)

        except tf.compat.v1.errors.ResourceExhaustedError:
            # just return the number of eggs as None
            pass

        return num_eggs

    def get_worm_location_and_count_eggs(self, image, frame_no):
        worm_center_x, worm_center_y = (None, None)
        num_eggs = None
        image = self._prep_image(image)
        expanded_image = np.expand_dims(image, axis=0)
        try:
            classes, boxes, scores = self._run(expanded_image)

            target_class = 2
            min_score = 0.8
            num_eggs, egg_classes, egg_boxes, egg_scores = self._screen_results(target_class, min_score, classes, boxes, scores)
            target_class = 1
            min_score = 0.8
            num_worms, worm_classes, worm_boxes, worm_scores = self._screen_results(target_class, min_score,
                                                                                    classes, boxes, scores)
            worm_class, worm_box, worm_score = self._get_top_result(num_worms, worm_classes, worm_boxes, worm_scores)

            if worm_box is not None:
                worm_center_x, worm_center_y = self._get_box_center(worm_box)

            if self.save_processed_images:
                with self.box_file_lock:
                    if exists(self.h5_file):
                        with h5py.File(self.h5_file, 'a') as hf:
                            if egg_boxes is not None:
                                frame_boxes_name = 'egg_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=egg_boxes)
                                frame_scores_name = 'egg_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=egg_scores)
                            if worm_box is not None:
                                frame_boxes_name = 'worm_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=worm_boxes)
                                frame_scores_name = 'worm_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=worm_scores)
                    else:
                        with h5py.File(self.h5_file, 'w') as hf:
                            if egg_boxes is not None:
                                frame_boxes_name = 'egg_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=egg_boxes)
                                frame_scores_name = 'egg_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=egg_scores)
                            if worm_box is not None:
                                frame_boxes_name = 'worm_boxes_frame_' + str(frame_no)
                                hf.create_dataset(frame_boxes_name, data=worm_boxes)
                                frame_scores_name = 'worm_score_frame_' + str(frame_no)
                                hf.create_dataset(frame_scores_name, data=worm_scores)

        except tf.compat.v1.errors.ResourceExhaustedError:
            # just return the center point as None, None and the number of eggs as None
            pass

        return num_eggs, worm_center_x, worm_center_y


