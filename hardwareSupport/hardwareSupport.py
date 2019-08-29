__author__ = 'kebates'
import serial
from serial.tools import list_ports
from kivy.logger import Logger
import time


class TeensyConfig(object):

    def __init__(self):
        self.ports = list_ports.comports()
        self.teensy_port = None
        try:
            for port in self.ports:
                # TODO may not be working on all systems?
                if port.manufacturer == 'Teensyduino':
                    self.teensy_port = port.device
                    Logger.debug("Teensy Config: Using serial port %s" % self.teensy_port)
        except IndexError:
            Logger.debug('Teensy Config: No serial connection found')


class TempSensor(object):

    def __init__(self, config):
        self.port = config.teensy_port

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

    def __init__(self, config, color='255;0;0', radius=5, mode='darkfield', linescan_int=16, do_timelapse='None'):
        self.port = config.teensy_port
        self.color = color
        self.radius = radius
        self.mode = mode
        self.linescan_int = linescan_int
        self.do_timelapse = do_timelapse
        self.matrix_width, self.matrix_height = 32, 32
        self.center_x, self.center_y = 16, 16
        init_commands = [{'matrix_mode': 'set_color', 'color': self.color},
                         {'matrix_mode': 'opto', 'is_on': '0'},
                         {'matrix_mode': 'set_radius', 'radius': str(self.radius)},
                         {'matrix_mode': self.mode}]
        self.send_command(init_commands)

    def send_command(self, mode_list):
        nline = '\n'
        # Logger.debug('LEDMatrix: matrix_mode is %s' % matrix_mode)
        with serial.Serial(self.port, baudrate=38400, timeout=0, writeTimeout=5) as ser:
            for mode in mode_list:
                ser.flushInput()
                ser.flushOutput()
                time.sleep(0.05)
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


