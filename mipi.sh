#!/bin/bash

cd ~/mi-pi
echo "Making sure google sheets token is available..."
# check whether there's a token file
if [ -f "token.pickle" ]; then
    echo "Credentials file exists, let's make sure they're valid! You'll need to be on the internet"
    python3 setup_google_sheets.py
else
    echo "Opening browser so you can download your credentials. You just need to complete Step 1 of this Guide. Save the downloaded file to the /mi-pi/ folder."
    chromium-browser -url "https://developers.google.com/sheets/api/quickstart/python"
    echo "Is the credentials.json file saved in /mi-pi/? [Y(es)/ N(o)]"
    read credentials_saved
    if [ "$credentials_saved" == "y" ]; then
        python3 setup_google_sheets.py
    fi
fi

echo "Making sure rclone is configured..."
# check for config file
if [ -f "/home/pi/.config/rclone/rclone.conf" ]; then
    rclone listremotes
    echo "If you've already configured a cloud service to upload to, you should see it above. If you don't see the cloud service you want to save videos to above, please run 'rclone config' in the terminal."
else
    echo "Rclone isn't configured yet - let's set it up so that you can upload data to a cloud storage account. You should likely use the default setup for whichever cloud service you have. Take note of the name you give your remote!"
    rclone config
fi

export PYTHONPATH=$PYTHONPATH:'/home/pi/models/research':'/home/pi/models/research/slim'

echo "Opening FLEET..."

python3 main.py