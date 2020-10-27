__author__ = 'kebates'
import serial
from serial.tools import list_ports
from kivy.logger import Logger
import time
import smbus


class TeensyConfig(object):

    def __init__(self):
        self.ports = list_ports.comports()
        try:
            for port in self.ports:
                # TODO may not be working on all systems?
                if port.manufacturer == 'Teensyduino':
                    self.teensy_port = port.device
                    Logger.debug("Teensy Config: Using serial port %s" % self.teensy_port)
            if 'self.teensy_port' not in locals():
                self.use_teensy = False
                self.teensy_port = None
        except IndexError:
            Logger.debug('Teensy Config: No serial connection found')
            self.use_teensy = False
            self.teensy_port = None


class TempSensor(object):

    def __init__(self, config):
        self.port = config.teensy_port
        if config.teensy_port == None:
            self.use_teensy = False
            self.temp_sensor_address = self.get_i2c_address()

    def receive_serial(self, info):
        # read from serial port
        try:
            with serial.Serial(self.port, baudrate=38400, timeout=1, writeTimeout=5) as ser:
                ser.flushInput()
                ser.flushOutput()
                line = ser.readline()
                msg = line.decode("utf-8")
                # split end stuff from the line and only take the front end
                lines = line.rsplit(b'\r')
                # parse serial message into temp and humidity
                msg_list = lines[0].split(b',')
                Logger.debug("Msg_list is: %s" % msg_list)
                if len(msg_list) == 2:
                    for j in msg_list:
                        msg_parts = j.split(b':')
                        info[msg_parts[0].decode('utf-8')] = float(msg_parts[1])
                    return info, True
                else:
                    return info, False
        except serial.serialutil.SerialException or IndexError:
            return info, False

    def get_i2c_address(self):
        self.bus = smbus.SMBus(1)
        for device in range(128):
            try:
                self.bus.read_byte(device)
                i2c_address = hex(device)
            except:
                pass
        if i2c_address in locals():
            Logger.info('i2c device address is' + str(i2c_address) )
        else:
            Logger.debug('TempSensor: no i2c device found. check GPIO connections. You can run sudo i2cdetect -y 1 from the command line')
        return i2c_address

    def get_temperature_humidity(self, info):
        #read from GPIO
        try:
            read_temp_command = 0xE3
            read_humidity_command = 0xE5
            temp_bytes = self.bus.read_i2c_block_data(self.temp_sensor_address, read_temp_command, 2)
            humidity_bytes = self.bus.read_i2c_block_data(self.temp_sensor_address, read_humidity_command, 2)

            temp_C = self.bytes_to_C(temp_bytes)
            humidity_percent = self.bytes_to_percent(humidity_bytes)
            info['temperature'] = temp_C
            info['humidity'] = humidity_percent

            Logger.debug('TempSensor: temp is ' + str(temp_C))
            Logger.debug('TempSensor: humidity is ' + str(humidity_percent))
            return info, True
        except:
            return info, False

    def bytes_to_C(self, bytes):
        word = (bytes[0] << 8) + bytes[1]
        return (175.72*word/65536) - 46.85         # temp in celcius

    def bytes_to_percent(self, bytes):
        word = (bytes[0] << 8) + bytes[1]
        return (125*word/65536) - 6        # humidity in percent

class LEDMatrix(object):

    def __init__(self, config, color='255;0;0', radius=5, center=(16, 16), mode='darkfield', linescan_int=16, do_timelapse='None'):
        self.port = config.teensy_port
        if self.port == None:
            self.use_teensy = False
        else:
            self.use_teensy = True
        self.color = color
        self.radius = radius
        self.mode = mode
        self.linescan_int = linescan_int
        self.do_timelapse = do_timelapse
        self.matrix_width, self.matrix_height = 32, 32
        self.center = ';'.join([str(center[0]), str(center[1])])
        init_commands = [{'matrix_mode': 'set_color', 'color': self.color},
                         {'matrix_mode': 'set_center', 'center': self.center},
                         {'matrix_mode': 'opto', 'is_on': '0'},
                         {'matrix_mode': 'set_radius', 'radius': str(self.radius)},
                         {'matrix_mode': self.mode}]
        if self.use_teensy:
            self.send_command(init_commands)
            Logger.debug('LED Matrix: tried to send command hardwareSupport.py line 76')

    def send_command(self, mode_list):
        if not self.use_teensy:
            Logger.debug('LEDMatrix: tried to use LED without teensy')
            return

        nline = '\n'
        # Logger.debug('LEDMatrix: matrix_mode is %s' % matrix_mode)
        with serial.Serial(self.port, baudrate=38400, timeout=0, writeTimeout=5) as ser:
            for mode in mode_list:
                ser.flushInput()
                ser.flushOutput()
                time.sleep(0.5)
                if mode['matrix_mode'] == 'solid':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'calibrate':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'DPC':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'dark_DPC':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'brightfield':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'darkfield':
                    msg = ';'.join([mode['matrix_mode'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'set_color':
                    self.color = mode['color']
                    msg = ';'.join([mode['matrix_mode'], mode['color'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'set_center':
                    self.center = mode['center']
                    msg = ';'.join([mode['matrix_mode'], mode['center'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'set_radius':
                    self.radius = int(mode['radius'])
                    msg = ';'.join([mode['matrix_mode'], mode['radius'], nline])
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                    ser.write(msg.encode())
                elif mode['matrix_mode'] == 'opto':
                    msg = ';'.join([mode['matrix_mode'], mode['is_on'], nline])
                    ser.write(msg.encode())
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                elif mode['matrix_mode'] == 'linescan_bright':
                    msg = ';'.join([mode['matrix_mode'], str(self.linescan_int), nline])
                    ser.write(msg.encode())
                    Logger.debug('LEDMatrix: msg is %s' % msg)
                elif mode['matrix_mode'] == 'linescan_dark':
                    msg = ';'.join([mode['matrix_mode'], str(self.linescan_int), nline])
                    ser.write(msg.encode())
                    Logger.debug('LEDMatrix: msg is %s' % msg)


