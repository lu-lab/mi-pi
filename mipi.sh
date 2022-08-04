#!/bin/bash

cd ~/mi-pi

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