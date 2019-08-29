#Software Installation

Once you have constructed the physical aspects of the system, you're ready to install software. For the full capabilities of the system, there are two locations you will need to install software:
- on each Raspberry Pi
- on a single remote computer

If you only need the continuous imaging capabilities of the system and the simple feedback capability, you can skip the installation steps for the remote computer entirely. However, if you want the advanced feedback capabilities and concurrent behavior tracking (as opposed to motion detection), you will need to follow steps for installation on the remote computer as well. 

## Remote Computer
### Install [Tierpsy-Tracker](https://github.com/ver228/tierpsy-tracker/tree/2e88a070f9b191cfd3d13bc0b7545a6cb30a472c) on your remote computer

This software package is an easy-to-use and comprehensive package for behavior analysis of *C. elegans*, zebrafish, and *Drosophila* larvae. Follow the directions [here](https://github.com/ver228/tierpsy-tracker/blob/2e88a070f9b191cfd3d13bc0b7545a6cb30a472c/docs/INSTALLATION.md) to install on your computer. 
- we recommend testing the installation as directed on this page to make sure it works as expected.

### Download the script [remote_analysis]()


## Raspberry Pi

Almost all of the software packages you need are already installed, assuming you've imaged your microSD card using the image provided (see [Building the Hardware](/docs/hardware.md)). However, there are still a few things to set up before you can experiment.
### Link to Google Sheets
 You will need to set up Google Sheets so that you can access a sheet remotely. 
 - first, we'll run a script that will take you to a Google sign-in page to allow access to your Google Drive
 - then, we'll set-up a Google Sheet to link your system to
 - last, we'll copy the Google Sheet ID into your "keys.py" file
    > https://docs.google.com/spreadsheets/d/spreadsheetId/edit#gid=0

### Set-up rclone 
1. Open the terminal on the Raspberry Pi and type: 

        curl https://rclone.org/install.sh | sudo bash
2. To configure your remote cloud storage, type the following in the terminal:

        sudo rclone config
        
    and follow the prompts. Take a note of what you name your remote, as it will be important later during experiment set-up! It is easiest to use the default dropbox configuration, which will take you to an authentication server (open a web browser) during the configuration. 
3. Make sure it works! 