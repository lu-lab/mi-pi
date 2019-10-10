import json

expSettings_json = json.dumps([
    {'type': 'title',
     'title': 'Worm Info'},
    {'type': 'string',
     'title': 'Strain',
     'desc': 'strain identifier',
     'key': 'strain',
     'section': 'worm info'},
    {'type': 'string',
     'title': 'Genotype',
     'desc': 'specific genotype',
     'key': 'genotype',
     'section': 'worm info'},
    {'type': 'options',
     'title': 'Sex',
     'desc': '(H)ermaphrodite or (M)ale',
     'key': 'wormsex',
     'options': ['H', 'M'],
     'section': 'worm info'},
    {'type': 'options',
     'title': 'Worm Stage',
     'desc': 'developmental stage of animals',
     'key': 'wormstage',
     'options': ['egg', 'L1', 'L2', 'L3', 'L4', 'adult'],
     'section': 'worm info'},
    {'type': 'string',
     'title': 'Additional Comments',
     'desc': 'other conditions of note',
     'key': 'wormcomment',
     'section': 'worm info'},


    {'type': 'title',
     'title': 'Experiment Settings'},
    {'type': 'string',
     'title': 'System ID',
     'desc': "this system's unique identifier",
     'section': 'experiment settings',
     'key': 'systemid'},
    {'type': 'string',
     'title': 'Physical environment',
     'desc': 'microfluidic, agar, droplet, etc.',
     'section': 'experiment settings',
     'key': 'physical'},
    {'type': 'path',
     'title': 'Local Experiment Folder',
     'desc': 'local folder path where you would like to store experiment data',
     'section': 'experiment settings',
     'key': 'local_exp_path'},
    {'type': 'string',
     'title': 'Remote Experiment Folder',
     'desc': 'remote folder path where you would like to store experiment data',
     'section': 'experiment settings',
     'key': 'remote_exp_path'},
    {'type': 'numeric',
     'title': 'Experiment length',
     'desc': 'how long is the experiment (in minutes)?',
     'section': 'experiment settings',
     'key': 'experimentlength'},
    {'type': 'string',
     'title': 'Google spreadsheet ID',
     'desc': 'spreadsheet id for sheet containing parameters',
     'section': 'experiment settings',
     'key': 'google_spreadsheet_id'},
    {'type': 'string',
     'title': 'rclone remote name',
     'desc': 'the name of the remote backup created in rclone',
     'section': 'experiment settings',
     'key': 'rclone_remote_name'}
])

imagingSettings_json = json.dumps([
    {'type': 'title',
     'title': 'LED matrix'},
    {'type': 'string',
     'title': 'LED color',
     'desc': 'as an 8-bit comma separated RGB triplet, i.e. 255, 0, 0 for red',
     'section': 'LED matrix',
     'key': 'ledcolor'},
    {'type': 'numeric',
     'title': 'Darkfield/ brightfield circle pixel radius',
     'desc': 'If system is calibrated and pixel radius is known',
     'section': 'LED matrix',
     'key': 'matrixradius'},
    {'type': 'numeric',
     'title': 'center x',
     'desc': 'x position of matrix center',
     'section': 'LED matrix',
     'key': 'ledx'},
    {'type': 'numeric',
     'title': 'center y',
     'desc': 'y position of matrix center',
     'section': 'LED matrix',
     'key': 'ledy'},

    {'type': 'title',
     'title': 'Timelapse imaging'},
    {'type': 'options',
     'title': 'timelapse imaging options',
     'desc': 'LED matrix options for timelapse imaging',
     'section': 'LED matrix',
     'key': 'timelapse_options',
     'options': ['None', 'brightfield', 'darkfield', 'linescan']},
    {'type': 'numeric',
     'title': 'image frequency',
     'desc': 'in seconds',
     'section': 'LED matrix',
     'key': 'hc_image_frequency'},


    {'type': 'title',
     'title': 'Camera Settings'},
    {'type': 'numeric',
     'title': 'framerate',
     'desc': 'fps (integer)',
     'section': 'camera settings',
     'key': 'fps'},
    {'type': 'numeric',
     'title': 'Gain',
     'desc': 'Gain',
     'section': 'camera settings',
     'key': 'gain'},
    {'type': 'options',
     'title': 'Resolution',
     'desc': 'pixel w x h',
     'section': 'camera settings',
     'key': 'resolution',
     'options': ['3280x2464', '1640x1232', '1640x922']},
    {'type': 'numeric',
     'title': 'Video length',
     'desc': 'length of individual videos',
     'section': 'camera settings',
     'key': 'video_length'},
    {'type': 'numeric',
     'title': 'inter video interval',
     'desc': 'how much time (in seconds) between each video?',
     'section': 'camera settings',
     'key': 'inter_video_interval'},

    {'type': 'title',
     'title': 'Webstreaming'},
    {'type': 'bool',
     'title': 'Stream video to website?',
     'desc': 'if you would like to stream to a website, you must include a host below!',
     'section': 'webstreaming',
     'key': 'do_webstream'},
    {'type': 'string',
     'title': 'youtube livestream link',
     'desc': 'from live streaming dashboard',
     'section': 'webstreaming',
     'key': 'youtube_link'},
    {'type': 'string',
     'title': 'youtube livestream key',
     'desc': 'from live streaming dashboard',
     'section': 'webstreaming',
     'key': 'youtube_key'}
])

pressureSettings_json = json.dumps([
    {'type': 'title',
     'title': 'Pressure Control'},
    {'type': 'path',
     'title': 'File with control scheme',
     'desc': 'filepath',
     'section': 'pressure control',
     'key': 'pressurepath'}
    ])

imageProcessingSettings_json = json.dumps([
    {'type': 'title',
     'title': 'Image Processing'},
    {'type': 'options',
     'title': 'Online motion detection?',
     'desc': 'Which type (if any)?',
     'section': 'main image processing',
     'key': 'image_processing_mode',
     'options': ['None', 'image delta', 'image thresholding']},
    {'type': 'bool',
     'title': 'Link motion to blue light?',
     'desc': 'record motion with blue light feedback',
     'section': 'main image processing',
     'key': 'motion_with_feedback'},
    {'type': 'options',
     'title': 'Image resolution',
     'desc': 'resolution of images used in online processing',
     'section': 'main image processing',
     'key': 'image_resolution',
     'options': ['3280x2464', '1640x1232', '1640x922', '1280x720', '640x480']},
    {'type': 'bool',
     'title': 'Save raw images?',
     'desc': 'Save raw images used for image processing',
     'section': 'main image processing',
     'key': 'save_images'},
    {'type': 'numeric',
     'title': 'Image frequency',
     'desc': 'integer in seconds defining frequency of images used for image analysis',
     'section': 'main image processing',
     'key': 'image_frequency'},
    {'type': 'bool',
     'title': 'Is this the driving system?',
     'desc': 'the driving system will control illumination dosage on the paired system',
     'section': 'main image processing',
     'key': 'is_driving_system'},
    {'type': 'numeric',
     'title': 'Check LED dosage interval',
     'desc': 'frequency (in minutes) to check the LED dosage of the paired system',
     'section': 'main image processing',
     'key': 'check_dosage_interval'},
    {'type': 'numeric',
     'title': 'low motion prior',
     'desc': 'estimate of percent time spent in low motion state (used until first check LED dosage interval)',
     'section': 'main image processing',
     'key': 'sleep_prior'},
    {'type': 'numeric',
     'title': 'max blue light exposure',
     'desc': 'maximum percent light dosage',
     'section': 'main image processing',
     'key': 'max_exposure'},
    {'type': 'numeric',
     'title': 'LED on time',
     'desc': 'duration of each LED ''on'' cycle in seconds',
     'section': 'main image processing',
     'key': 'led_on_time'},
    {'type': 'string',
     'title': 'Paired system ID',
     'desc': 'for light perturbation experiments',
     'section': 'main image processing',
     'key': 'paired_systemid'},

    {'type': 'title',
     'title': 'Image Delta Processing'},
    {'type': 'numeric',
     'title': 'Threshold for delta magnitude',
     'section': 'image delta',
     'key': 'delta_threshold'},
    {'type': 'numeric',
     'title': 'threshold for pixel number > delta magnitude',
     'section': 'image delta',
     'key': 'num_pixel_threshold'},

    {'type': 'title',
     'title': 'Image Thresholding'},
    {'type': 'numeric',
     'title': 'threshold block size',
     'desc': 'meh',
     'section': 'image thresholding',
     'key': 'thresh_block_size'},
    {'type': 'bool',
     'title': 'keep border data?',
     'desc': 'if blobs are on the border, keep them?',
     'section': 'image thresholding',
     'key': 'keep_border_data'},
    {'type': 'numeric',
     'title': 'minimum area',
     'desc': 'minimum area for detected blobs',
     'section': 'image thresholding',
     'key': 'min_area'},
    {'type': 'numeric',
     'title': 'maximum area',
     'desc': 'maximum area for detected blobs',
     'section': 'image thresholding',
     'key': 'max_area'},
    {'type': 'numeric',
     'title': 'dilation size',
     'desc': 'expand blob size by this many pixels',
     'section': 'image thresholding',
     'key': 'dilation_size'},
    {'type': 'numeric',
     'title': 'initial xmin',
     'desc': 'initial value for cropping; change in next screen',
     'disabled': 'True',
     'section': 'image thresholding',
     'key': 'xmin'},
    {'type': 'numeric',
     'title': 'initial xmax',
     'desc': 'initial value for cropping; change in next screen',
     'disabled': 'True',
     'section': 'image thresholding',
     'key': 'xmax'},
    {'type': 'numeric',
     'title': 'initial ymin',
     'desc': 'initial value for cropping; change in next screen',
     'disabled': 'True',
     'section': 'image thresholding',
     'key': 'ymin'},
    {'type': 'numeric',
     'title': 'initial ymax',
     'desc': 'initial value for cropping; change in next screen',
     'disabled': 'True',
     'section': 'image thresholding',
     'key': 'ymax'},
    {'type': 'numeric',
     'title': 'initial threshold constant',
     'desc': 'initial value for threshold constant; change in next screen',
     'disabled': 'True',
     'section': 'image thresholding',
     'key': 'image_threshold'}
    ])
