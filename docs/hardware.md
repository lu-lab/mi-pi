# Building the Hardware
First we'll set up the physical aspects of the system, and put the operating system image onto a microSD card
**Note that in this section when you download software, it should be to a computer other than a Raspberry Pi that has USB inputs**

## Build the Lego set
### Supplies
- Legos are listed [here](enclosure%20lego%20parts.csv). This list can be uploaded to [BrickLink](https://www.bricklink.com/v2/main.page) as a ['Wanted List'](https://www.bricklink.com/help.asp?helpID=1) that you can easily buy. 
### Directions
The assembled set will look like the following:
![Lego single setup](/docs/assembly%20images/enclosure_v2.png)  
A single baseplate can accomodate 4 microscopes, and the assembled legos will look like so: 
![Lego quad setup](/docs/assembly%20images/quad_enclosure.png)  
Follow these pictorial directions to assemble the set (model and directions produced with Stud.io):  
![Lego step 1](/docs/assembly%20images/lego_step1.png)
![Lego step 2](/docs/assembly%20images/lego_step2.png)
![Lego step 3](/docs/assembly%20images/lego_step3.png)
![Lego step 4](/docs/assembly%20images/lego_step4.png)
![Lego step 5](/docs/assembly%20images/lego_step5.png)
![Lego step 6](/docs/assembly%20images/lego_step6.png)
![Lego step 7](/docs/assembly%20images/lego_step7.png)
![Lego step 8](/docs/assembly%20images/lego_step8.png)
![Lego step 9](/docs/assembly%20images/lego_step9.png)
![Lego step 10](/docs/assembly%20images/lego_step10.png)
![Lego step 11](/docs/assembly%20images/lego_step11.png)
![Lego step 12](/docs/assembly%20images/lego_step12.png)
![Lego step 13](/docs/assembly%20images/lego_step13.png)
![Lego step 14](/docs/assembly%20images/lego_step14.png)
![Lego step 15](/docs/assembly%20images/lego_step15.png)
![Lego step 16](/docs/assembly%20images/lego_step16.png)
![Lego step 17](/docs/assembly%20images/lego_step17.png)
\

## Assemble the temperature sensor and bright blue LED strip
### Supplies
- 1/3 of a [Neon-like blue LED strip](https://www.adafruit.com/product/3867)
- 1 [LED driver](https://www.sparkfun.com/products/13716)
- 1 [Screw Terminal 3.5mm pitch](https://www.sparkfun.com/products/8084)
- 1 [temperature and humidity sensor](https://www.sparkfun.com/products/13763)
- 8 [angled headers](https://www.sparkfun.com/products/553) (any supplier will do)
- 8 [M/F jumper wires](https://www.sparkfun.com/products/9139) (any supplier will do)
- 1 [Female DC Power jack to screw terminal block](https://www.adafruit.com/product/368)
- small Phillips and flathead screwdrivers
- soldering iron and solder
- ~5 inches of red and black 20G-22G wire (preferably solid core)
- wire strippers and wire cutters
- (electrical tape or heat shrink tubing)
### Directions
1. Solder angled headers and terminal block to LED driver and temperature and humidity sensor. Soldering instructions [here](https://www.youtube.com/watch?v=BLfXXRfRIzY).
![image of LED driver and temp sensor pre-soldering](/docs/assembly%20images/temp_humidity.jpg)
2. On the back of the blue LED strip, mark the black lines that divide the strip into approximately thirds. ![back of LED strip](/docs/assembly%20images/LED_strip_precut2.jpg)
3. With the already-soldered wires to the right and the fully sealed end of the strip to the left, first cut completely through the LED strip ~1/4 inch to the right of one of your marks with a scalpel or craft knife (along red dotted line). ![cut LED strip](/docs/assembly%20images/LED_strip_cut.jpg)
4. Cut through the silicone housing (but not the inner strip) ~1/4 inch to the left of the mark (yellow dotted line). Pull off the silicone housing to expose the soldering pads. ![cut silicone housing](/docs/assembly%20images/LED_strip_housing.jpg)
5. Cut ~5 inch pieces of black and red wire and strip ~1/4 inch off both ends. ![cut and stripped wire]()
6. Solder one end to the solder pad that's closer to the blue side of the silicone housing.
9. Cut a ~5 inch piece of red wire and strip ~1/4 inch off both ends. Solder one end to the solder pad that's farther from the blue side of the silicone housing. ![wires soldered to LED strip](/docs/assembly%20images/IMG_20190504_142847.jpg)
10. Insert the unsoldered ends of the red and black wired into the screw terminal you soldered onto the LED driver (red goes to +, black goes to -). ![]()
11. Screw the wire into place.
12. Take 4 differently colored jumper wires and attach the female ends to the headers soldered to the LED driver. The board is marked with the symbols V+ and V- (to power the LEDs), and D+ and D- (to control whether the LEDs are on or off). I strongly recommend using black and red jumper wires for the V- and V+ headers. Pictured below is the LED driver with black connected to V-, red connected to V+, yellow connected to ... and green connected to ...
13. Using wire cutters, cut close to the male end of the black and red wires and then strip ~0.25 inch of the insulation off using your wire stripper. Twist the strands of the wire together. Grab your power jack to screw terminal block and screw the stripped red wire into the side marked (+) and the stripped black wire into the side marked (-). If you have any exposed wire, use electrical tape or heat-shrink tubing to cover it. 
14. Now grab your temperature and humidity sensor and attach 4 differently colored jumper wires to the headers we soldered on earlier. Again, black jumper should go to GND and red jumper should go to PWR. In the picture below, green goes to () and yellow goes to (). 
15. Set the LED strip and the temperature sensor aside for now - we will attach them to the microcontroller at the end of the next step. ![humidity and temperature sensor with jumper wires](/docs/assembly%20images/IMG_20190504_150804.jpg)
## Set-up the LED matrix
### Supplies
- 1 microUSB to USB A cable (data capable)
- 1 [Teensy 3.5 with/ without headers](https://www.adafruit.com/product/3267) (several older Teensy models should also be ok. If you choose to buy without headers, you will have to buy and solder headers on yourself.)
- 1 [32x32 RGB LED Matrix](https://www.adafruit.com/product/607)
- 1 [SmartMatrix SmartLED Shield](https://www.adafruit.com/product/1902)
- 1 [Terminal connector](https://www.digikey.com/product-detail/en/te-connectivity-amp-connectors/1776293-1/A112765-ND/1649088)
- 1 [M/F jumper wires](https://www.sparkfun.com/products/9139) (any supplier will do)
- 1 [5V 2A power supply for SmartMatrix](https://www.adafruit.com/product/276) (optional)
    - the SmartMatrix can be powered from the Raspberry Pi itself, however, the power draw is high enough that the Raspberry Pi may crash. The LED array will be brighter powering from a separate source as well.
### Directions
#### Program the Teensy microcontroller
1. Download the [Teensyduino](https://www.pjrc.com/teensy/teensyduino.html) software. *Make sure the Teensyduino software is compatible with the version of Arduino you download. The Teensyduino versions can lag behind on occasion.*
2. Download the appropriate [Arduino IDE](https://www.arduino.cc/en/Main/Software) software for your operating system.
    1. Unfortunately, the web IDE is not compatible with Teensy boards. 
3. Make sure your Teensy is working by uploading 'Blink' example in the Arduino IDE. It may already be running when you first power up the Teensy, in which case you'll see the LED on the Teensy board blink on and off.
4. Install necessary libraries in your Arduino software
    1. Import the SmartMatrix library, as described in Arduino's documentation [here](https://www.arduino.cc/en/Guide/Libraries)
    2. Similarly, import the SparkFun_Si7021_Breakout_Library
5. Upload [control script](teensy_control.ino) to the Teensy
#### Attach Teensy to LED Matrix
Additional details here: http://docs.pixelmatix.com/SmartMatrix/shield-v4.html
#### Attach blue LED string and temperature and humidity sensor to Teensy
The pins that the jumper wires are connected to are important - if you connect something to the wrong pin, the blue LED string and temperature sensor may not work! 
1. First, we'll connect both the temperature sensor GND pin and the D- pin on the LED driver to the Teensy GND. 
    1. Cut the male headers off of both of the black jumper cables (connected to the LED driver and temperature sensor)with wire cutters and strip ~ 0.25 inches of insulation off the wire. 
    2. Connect the male end of a black jumper cable to GND on the Teensy. Cut the female end off with wire cutters and strip ~0.25 inch of the insulation off. 
    3. Twist all three exposed wires (LED driver GND, temp sensor GND, and Teensy GND) together, and screw into the terminal connector on either side. 
2. Here are all the connections and corresponding images:

    | Temperature and humidity sensor pin | Teensy pin |
    | --- | --- |
    | GND | Teensy GND |
    | 3.3V | Teensy 3.3V |
    | SDA | Teensy 18 |
    | SCL | Teensy 19 |

    | LED driver pin | Teensy pin |
    | --- | --- |
    | D- | Teensy GND |
    | D+ | Teensy 23 |
    | V+ | barrel jack + |
    | V- | barrel jack - |
## Set-up microSD card
### Supplies
- microSD card reader/writer
- microSD card (at least 32 GB)
### Directions
**Remember when handling the microSD card that it is very sensitive to static damage! Make sure to ground yourself before touching it.**

1. Download the [Raspberry Pi operating system image](cheapscope_03112019.zip) and unzip it.
2. Following the directions under [*Writing an image to the SD card*](https://www.raspberrypi.org/documentation/installation/installing-images/), flash the image to the microSD card. 
3. If you're using a 32GB microSD, you're done setting up the microSD card! If you're using a microSD card of a size greater than 32GB, you will need to manually expand the file system to use the full microSD card. If you need to do this, you will need to have a second microSD card with a working Raspbian operating system. Put the microSD card whose filesystem you want to expand in a USB microSD card reader and the other microSD card in your Raspberry Pi and boot the Raspberry Pi.
    1. Once the Raspberry Pi has booted, open the terminal and enter:
    
            sudo apt-get update
            sudo apt-get upgrade
            sudo apt-get install gparted
            sudo gparted
    2. The user interface for gparted should open. First choose the correct microSD card to edit. 
    3. Unmount all partitions on this drive by right-clicking the key icon and selecting 'Unmount'.
    4. Expand the partition /dev/sdc2/ as far to the right as possible. Click the checkmark to expand. 
    5. Expand the /dev/sdc7/ (root) partition as far to the right as possible. Click the checkmark to expand. 
    6. You should now see that the root partition fills most of the microSD card's space. 
    7. Remove your USB microSD card reader from the Raspberry Pi's USB port and remove the microSD

## Build and install the Raspberry Pi case

### Supplies
- [Raspberry Pi SmartiPi Touch case with Lego Compatible Front](https://www.adafruit.com/product/3576)
- [Raspberry Pi 3 ](https://www.adafruit.com/product/3055) (model B+ should also work, we have not yet tested with Raspberry Pi 4, but it's in progress)
- [Raspberry Pi camera v2](https://www.adafruit.com/product/3099)
- [Raspberry Pi camera lens adjustment tool](https://www.adafruit.com/product/3518)
- [Raspberry Pi offical touchscreen](https://www.adafruit.com/product/2718)
- several medium command strips, for example [these](https://www.amazon.com/Command-Medium-Mounting-Refill-18-Strip/dp/B013MMDQTY/ref=pd_sbs_200_5/143-6066223-1703664?_encoding=UTF8&pd_rd_i=B013MMDQTY&pd_rd_r=84255f50-cbac-49f6-b627-99d2edd06f3c&pd_rd_w=Ogypt&pd_rd_wg=hK7Xy&pf_rd_p=1c11b7ff-9ffb-4ba6-8036-be1b0afa79bb&pf_rd_r=AZ3WAW3WPTER5EZF5WKD&psc=1&refRID=AZ3WAW3WPTER5EZF5WKD)
- tweezers
- microSD card prepared in previous step
- 5V, 3A power supply w/ microUSB 
- assembled Lego set
- assembled LED matrix

### Directions
1. Carefully insert the prepared microSD cards into the microSD card slot on the Raspberry Pi.
2. Assemble the Raspberry Pi Touchscreen and Raspberry Pi in the SmartiPi Touch case [as described here](https://www.youtube.com/watch?v=XKVd5638T_8)
3. Insert the camera board into the lego-compatible camera case. Attach the camera case to the lego set as shown. ![camera placed in lego set]()
4. Remove the protective film from the camera lens with tweezers.
5. Attach the camera's ribbon cable to the back of the Raspberry Pi. See directions [here]() for how to attach ribbon cables. 
6. Remove the 'Wall' side of the command strips and attach to the smooth 2x3 Lego tiles and press about 10 seconds.
7. Allow to set several minutes.
8. Remove the other side of the command strips and press the feet of the Raspberry Pi case onto it. 
9. If using ethernet, plug in cable now; plug Raspberry Pi into 5V 3A power supply.
10. Congrats! All the physical parts of the system are now built. Now, we'll test and setup the software and hardware in the [installation docs](installation.md)
