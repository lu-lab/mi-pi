# Use it!

Now the system is built, using it is simple. 

## Open the software

1. To open the software, double tap this icon: 
![mi-pi icon](icons/simpleicon.png)

2. If this is your first time using the software, you will first be guided through setup of a cloud storage sync service (rclone) and Google Sheets. You will need internet access. The instructions below should appear in the terminal, but you can follow the directions here as well. 
    1. You will configure rclone in the terminal. Typically, we recommend that you follow the 'default' recommendations. Write down the name that you give your cloud sync service, as you will need to enter it in mi-pi's settings. If you forget, or don't know, you can open a terminal and run 
            
           rclone listremotes
           
    2. If in the future you would like to configure your mi-pi with a different cloud service, you can open a terminal and type
        
           rclone config
        this will take you through the set-up process again. Remember to write down your new remote's name and update it in mi-pi settings.           
    3. Once rclone has been configured, you should see a webpage open to a page titled 'Python Quickstart'. If it doesn't open for whatever reason, follow this link: [Python Quickstart](https://developers.google.com/sheets/api/quickstart/python).
    4. Click the button under the heading **Step 1: Turn on the Google Sheets API**, **Enable the Google Sheets API**. You will be asked to login to a google account and download the file *credentials.json*. Save this file in the **mi-pi** folder in the **home** folder of your Pi.
    5. You'll then be asked to complete authentication for the Google account you previously set up.
2. You should now see an interface open that looks like this:
![mi-pi software main screen]()

3. Before you can run an experiment, you will need to open the 'Settings' tab, where you can both enter metadata and set camera and feedback parameters (See the table below for options and recommended settings). Tap the Settings icon to open it.

Setting Name | Setting Description | Options | Recommended value
-------------|-----------|----------------|--------------------
Strain |strain identifier | any string | N/A
Genotype | genotype of animals | any string | N/A
Sex | sex of animals | (H)ermaphrodite, (F)emale or (M)ale| N/A
Developmental Stage | developmental stage of animals| 'egg', 'L1', 'L2', 'L3', 'L4', 'adult'| N/A
Additional Comments | other conditions of note | any string | N/A
System ID |this system's unique identifier, which must match the first part of your spreadsheet tab's name | any string | N/A
Physical environment | description of the behavior environment | any string | N/A
Local Experiment Folder | local folder path where you would like to store experiment data | any folder path | /home/pi
Remote Experiment Folder | remote folder path where you would like to store experiment data - this folder should already exist on the cloud service | valid folder path on your cloud service | N/A
Experiment length | how long is the experiment (in minutes) | any integer | N/A
Google Sheet ID | spreadsheet id for Google sheet containing parameters, look [here](https://developers.google.com/sheets/api/guides/concepts) for where to find it in your spreadsheet| alphanumeric string | N/A
Rclone remote name | the name of the cloud service configured in rclone | string | N/A
LED color | color of the LED matrix | as an 8-bit comma separated RGB triplet, i.e. 255, 0, 0 for red | 255, 0, 0
Darkfield/ brightfield circle pixel radius | To image in darkfield or brightfield, we only illuminate some LEDs in the matrix - this helps define which ones to illuminate. It depends on the imaging mode, which can be set on your Google Sheet. | integer between 1 and 16 | 10
center x | defines the center pixel of the radius's x position | integer between 1 and 32 | 16
center y | defines the center pixel of the radius's y position | integer between 1 and 32 | 16
timelapse imaging options | LED matrix mode options for timelapse imaging. If this is anything other than 'None', the system will not record video | None, brightfield, darkfield, linescan | None
timelapse image frequency | how many seconds between each image for timelapse imaging? | any integer | N/A
framerate | framerate of video collection (fps) | integer typically beween 10 and 30 | 20
Resolution | camera resolution in pixels w x h |3280x2464, 1640x1232, 1640x922 | 1640x1232
Video length | length of individual videos (in seconds) - as the system is designed for long-term imaging, we chunk videos into shorter times to make it easy to upload to cloud storage. You can choose to only intermittently collect video by setting a *inter-video interval* below. | between 10 and 30 to prevent memory issues | 20
inter video interval | how much time (in seconds) between each video? | any number | 0-30 tested
Stream video to website? | if you would like to stream to a website, switch this to 'on'. We recommend NOT using this if you're also using Faster R-CNN. To use this, you need to provide a YouTube link and a YouTube key | On or Off | N/A
youtube livestream link | You can find this on YouTube's live streaming dashboard | string | N/A
youtube livestream key | You can find this on YouTube's live streaming dashboard | string | N/A
Online motion detection? | Choose the type of motion detection you want to run online. None means the system will record video, but won't do any further processing | None, image delta, Faster R-CNN, Mobilenet v2 | See the guide below
Link motion to blue light? | If set to 'off', the system will do online processing, but won't stimulate animals with blue light. If set to 'on', animals will be stimulated with blue light in accordance with the 'is this the driving system?' option | On / Off | N/A
Image resolution | camera resolution to use for images used in 'image delta' and 'Faster R-CNN' image processing |3280x2464', '1640x1232', '1640x922', '1280x720', '640x480' | 1640 x 1232
Save raw images? | Whether to save raw images used for image processing. If 'on', raw images will be saved. May be useful for additional post-processing | On / Off | N/A
Save processed images? | Whether to save images processed according to the type of online motion detection selected. For Faster R-CNN or Mobilenet processing, if this is 'on', bounding boxes of detected worms will be saved in a .hdf5 file | On / Off | N/A
Image frequency | integer in seconds defining frequency of images used for image analysis. Only used for Faster R-CNN and image delta.  | integer | See table below for typical speed of each processing method
Is this the driving system? | the animal on the driving system will see blue LED illumination in proportion to it's motion. The non-driving system will see blue LED illumination at the same dosage as the driving system, but distributed not in correlation to either animal's motion | On / Off | N/A
Check LED dosage interval | frequency (in minutes) to check the LED dosage of the paired driving system. This value is only used for systems that are not the driving system. Once the LED dosage of the paired driving system is checked, the non-driving system will change the frequency of illumination to match total dosage delivered to animal on driving system | integer | choose as appropriate for experiment
low motion prior | estimate of percent time spent in low motion state. This is used only by the non-driving system and only until the first check LED dosage interval. The better this estimate, the better the system will be at matching overall light dosage. | number between 0 and 100 (inclusive) | N/A
max blue light exposure | If you would like to set a maximum light dosage, this allows you to do so. Provide a percentile cut-off in terms of the total time LEDs are allowed on | number between 0 and 100 (inclusive) | N/A
LED on time | At each time interval specified on the Google Sheet, a decision is made to turn the blue LEDs on or not. If the blue LEDs are turned on, they will be turned on for this many seconds, then turned off again. If the number of seconds specified is longer than the interval on the Google Sheet, the LEDs will only stay on as long as the Google-Sheet specified interval length | integer | N/A
Paired system ID | If you are doing a paired experiment where one animal is on a 'driving' system and another animal is on a 'non-driving' system, specify the name of the system this system is paired with | string | N/A
count number of eggs | estimate number of eggs in image - this is in beta-testing, we recommend not using it| On/ Off | Off
threshold distance for LED illumination | worm centroid movement greater than this many pixels prevents LED stimulation | integer | We typically use 5 pixels
Threshold for delta magnitude | Once grayscale images are subtracted from one another, what is the change in greyscale value that indicates a worm has moved? | integer | this will require significant tuning and is highly dependent on illumination. We recommend turning on 'Save processed images' so that you can more easily test different threshold levels.
threshold for pixel number > delta magnitude | Once a thresholded image has been calculated using the 'delta magnitude' threshold above, we have a binary image. This threshold describes how many 1-valued pixels in this image (indicating changes between processed images) will prevent the worms from being dosed with blue LED light | integer | this may require tuning and will depend on your experiment 


## Set up your Google Sheet
The format of the Google Sheet is important, as the code will be looking for specific values in specific places. We suggest that you copy a pre-formatted sheet to the Google Drive associated with your mi-pi linked Google account.
[Here](https://docs.google.com/spreadsheets/d/1ne2ahZuz05zb4sNluAAJho3JpB93wv7d-BxrVLOotpc/edit?usp=sharing) is the pre-formatted Google sheet. 

### Give your systems unique names that correspond to each tab in the sheet
In this example sheet, the two systems are named 'test' and 'test2'. In order for mi-pi to access the right tab of the sheet, you need to name the tabs as **system name**-parameters, so the corresponding tabs must be called 'test-parameters' and 'test2-parameters'. Before you can run an experiment, you also need to populate the 'Experimental Time', 'illumination mode', 'matrix red value', 'matrix green value', 'matrix blue value', and 'radius' columns for at least the length of your experiment. 
### Adding more systems
You can easily duplicate a sheet, rename it and your new system should be able to access the sheet as long as the Google Spreadsheet ID is correct and the system name matches the tab (i.e. test-parameters implies the name of the system is test)

## Preview and adjust camera focus 
Prepare your sample for imaging however you like. 

You may wish to capture an initial image. Tap the camera button to do so. The image will be stored on your remote cloud service in a folder named 

## Start the experiment!
Once all settings are correct and your sample is prepared, touch the 'Start Experiment' button. It may take up to a minute to complete the initialization of the experiment, so don't be concerned if you do not see an immediate response. Once an experiment is successfully started, the button text will change to 'Experimenting!'. If you do not see this after a minute, try pressing the button again or re-starting the program. 

Now, you can go relax. Get a coffee, maybe.

If you wish to change any illumination parameters while the experiment is running, you can do so using the Google Sheet. You can also monitor graphs of the temperature, humidity, and animal movement from the Google Sheet. If you have set up YouTube streaming, you should see the video feed begin after a few minutes. Video and image data from your experiment will be uploaded to your configured cloud service at the interval specified on your linked Google Sheet, so you should see videos and images update throughout the experiment (see the file structure below), and you should also see the configuration file (kivycam.ini) after the experiment starts.

Once the experiment has finished, check the folder on your cloud service that you entered in mi-pi's settings. You will see a file structure like this:

    Your-Remote-Directory
        +--system-name-1
            +--data
                +--unique-experiment-code
                    +--images
                        +--calibrate_1.png
                        +--calibrate_2.png
                        +--calibrate_3.png
                        +--processed
                           +--img1.png (imgs only for Faster R-CNN or image delta if 'save processed images' is on
                           +--img2.png
                           +--data.h5 (only for Faster R-CNN or Mobilenet v2 processing)
                        +--unprocessed
                           +--img1.png (imgs only for Faster R-CNN or image delta if 'save raw images' is on
                           +--img2.png
                    +--videos
                         +--VID_timestamp_1.h264
                         +--VID_timestamp_2.h264
                    +--exp_conditions.csv
                    +--kivy_datestamp.txt
                    +--kivycam.ini
                    
                    
The exp_conditions.csv file is a copy of the tab of the Google Sheet corresponding to this system. The kivy_datestamp.txt file is a copy of mi-pi's logs, which can be useful for troubleshooting. The kivycam.ini file contains all the mi-pi settings for each experiment. If you do not see some of these files, something went wrong. See the section on Troubleshooting.

At the moment, you **must close mi-pi** after the end of every experiment, otherwise the camera will not connect properly. When you set up a new experiment, the settings from a previous experiment will persist. 
