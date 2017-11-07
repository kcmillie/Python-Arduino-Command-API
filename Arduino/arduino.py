#!/usr/bin/env python
import logging
import itertools
import platform
import serial
import time
from serial.tools import list_ports
if platform.system() == 'Windows':
    import _winreg as winreg
else:
    import glob


log = logging.getLogger(__name__)


def enumerate_serial_ports():
    """
    Uses the Win32 registry to return a iterator of serial
        (COM) ports existing on this computer.
    """
    path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except WindowsError:
        raise Exception

    for i in itertools.count():
        try:
            val = winreg.EnumValue(key, i)
            yield (str(val[1]))  # , str(val[0]))
        except EnvironmentError:
            break


def build_cmd_str(cmd, args=None):
    """
    Build a command string that can be sent to the arduino.

    Input:
        cmd (str): the command to send to the arduino, must not
            contain a % character
        args (iterable): the arguments to send to the command

    @TODO: a strategy is needed to escape % characters in the args
    """
    if args:
        args = '%'.join(map(str, args))
    else:
        args = ''
    return "@{cmd}%{args}$!".format(cmd=cmd, args=args)


def find_port(baud, timeout):
    """
    Find the first port that is connected to an arduino with a compatible
    sketch installed.
    """
    if platform.system() == 'Windows':
        ports = enumerate_serial_ports()
    elif platform.system() == 'Darwin':
        ports = [i[0] for i in list_ports.comports()]
    else:
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    for p in ports:
        log.debug('Found {0}, testing...'.format(p))
        try:
            sr = serial.Serial(p, baud, timeout=timeout)
        except (serial.serialutil.SerialException, OSError) as e:
            log.debug(str(e))
            continue
        time.sleep(2)
        version = get_version(sr)
        if version != 'version':
            log.debug('Bad version {0}. This is not a Shrimp/Arduino!'.format(
                version))
            sr.close()
            continue
        log.info('Using port {0}.'.format(p))
        if sr:
            return sr
    return None


def get_version(sr):
    cmd_str = build_cmd_str("version")
    try:
        sr.write(cmd_str)
        sr.flush()
    except Exception:
        return None
    return sr.readline().replace("\r\n", "")


class Arduino(object):

    def __init__(self, baud=9600, port=None, timeout=3, sr=None):
        """
        Initializes serial communication with Arduino if no connection is
        given. Attempts to self-select COM port, if not specified.
        """
        if not sr:
            if not port:
                sr = find_port(baud, timeout)
                if not sr:
                    raise ValueError("Could not find port.")
            else:
                sr = serial.Serial(port, baud, timeout=timeout)
        sr.flush()
        self.sr = sr

    def version(self):
        return get_version(self.sr)

    def digitalWrite(self, pin, val):
        """
        Sends digitalWrite command
        to digital pin on Arduino
        -------------
        inputs:
           pin : digital pin number
           val : either "HIGH" or "LOW"
        """
        if val == "LOW":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("dw", (pin_,))
        self.sr.write(cmd_str)
        self.sr.flush()

    def analogWrite(self, pin, val):
        """
        Sends analogWrite pwm command
        to pin on Arduino
        -------------
        inputs:
           pin : pin number
           val : integer 0 (off) to 255 (always on)
        """
        if val > 255:
            val = 255
        elif val < 0:
            val = 0
        cmd_str = build_cmd_str("aw", (pin, val))

        self.sr.write(cmd_str)
        self.sr.flush()

    def analogRead(self, pin):  # model after digitalread
        """
        Returns the value of a specified
        analog pin.
        inputs:
           pin : analog pin number for measurement
        returns:
           value: integer from 1 to 1023
        """
        cmd_str = build_cmd_str("ar", (pin,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

        rd = self.sr.readline().replace("\r\n", "")
        return int(rd)

    def digitalRead(self, pin):
        """
        Returns the value of a specified
        digital pin.
        inputs:
           pin : digital pin number for measurement
        returns:
           value: 0 for "LOW", 1 for "HIGH"
        """
        cmd_str = build_cmd_str("dr", (pin,))

        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

        rd = self.sr.readline().replace("\r\n", "")
        return rd

    def pinMode(self, pin, val):
        """
        Sets I/O mode of pin
        inputs:
           pin: pin number to toggle
           val: "INPUT" or "OUTPUT"
        """
        if val == "INPUT":
            pin_ = -pin
        else:
            pin_ = pin
        cmd_str = build_cmd_str("pm", (pin_,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def pinModePullUp(self, pin):
        cmd_str = build_cmd_str("pp", (pin,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def close(self):
        if self.sr.isOpen():
            self.sr.flush()
            self.sr.close()

    def I2Csetup(self, addr):
        cmd_str = build_cmd_str("ac", (addr,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def I2Cwritehigh(self, addr):
        cmd_str = build_cmd_str("hc", (addr,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def I2Cwritelow(self, addr):
        cmd_str = build_cmd_str("ic", (addr,))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def I2CUnstick(self):
        cmd_str = build_cmd_str("un", (""))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

        rd = self.sr.readline().replace("\r\n", "")
        return rd

    def I2CScan(self):
        cmd_str = build_cmd_str("ick", (""))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

        test = []
        x = 0

        while(x != "done"):
            print x
            x = self.sr.readline().replace("\r\n", "")
            if x != "done":
                test.append(x)
        return test

    def ConfI2C(self, address, reg, highdata, lowdata):
        cmd_str = build_cmd_str("cic", (address, reg, highdata, lowdata))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def WriteI2C(self, address, reg, data):
        cmd_str = build_cmd_str("wic", (address, reg, data))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

    def getRegRaw(self, address, reg):
        cmd_str = build_cmd_str("grr", (address, reg))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()

        Raw = self.sr.readline().replace("\r\n", "")
        return Raw

    def SoftReset(self):
        cmd_str = build_cmd_str("res", (""))
        self.sr.flushInput()
        self.sr.write(cmd_str)
        self.sr.flush()
