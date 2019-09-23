#Software Installation

Once you have constructed the physical aspects of the system, you're ready to install software. We strongly recommend using the provided image of the system instead of installing required packages yourself, but we have provided a list of required dependencies.


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

### Clone or update the mi-pi repository
1. If you are starting from the image provided, you should not need to do this step, but if you would like to use the most up-to-date version of the software, you can pull the most recent version from GitHub. First, open a terminal and switch into the mi-pi directory:

        cd ~/mi-pi
2. Then, also in the terminal, type: 

        git pull origin master
Your software should now be up-to-date!

3. If you are not starting from the image provided, we'll just clone the software in this repository. Open the terminal on the Raspberry Pi (you should be in the /home/pi directory) and clone the mi-pi repository like so:

        git clone https://github.com/lu-lab/mi-pi.git
When you open the system file explorer, you should see a folder 'mi-pi' in the /home/pi directory. 

### If you're not using the image...
#### Make sure all the package requirements in this file are installed. 
#### Create a desktop shortcut 
This will make it much easier to open the software. All the files needed should be in the 'mi-pi' directory. 

1. Find the mipi.desktop and mipi.sh files in the 'mi-pi' directory. Copy and paste them onto the Raspberry Pi's desktop.

2. The .desktop file will run the .sh file when it is double clicked, but first we must make the .sh file executable and move it to a new directory. 
To make the .sh file executable, open a terminal on the Raspberry Pi and switch into the /Desktop directory, then make the .sh file executable:

        cd ~/Desktop
        sudo chmod u+x mipi.sh
        
3. Now move the mipi.sh file to the /usr/local/bin/ directory. Note that you will not be allowed to do this via drag and drop methods, so we'll do it in the terminal (you should still be in the Desktop directory):

        sudo mv mipi.sh /usr/local/bin/
    


        