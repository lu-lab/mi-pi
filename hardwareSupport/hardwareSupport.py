__author__ = 'kebates'
import serial
from serial.tools import list_ports
from kivy.logger import Logger
import time


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
        #note to Lucinda: do GPIO stuff here

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


