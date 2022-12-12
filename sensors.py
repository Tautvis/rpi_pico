"""Sensor library. Mainly shows examples how to use sensors."""
import machine, utils, time
from micropython import const


# ADC conversion from U16 value to [0-1] range. ADC is 12 bit but read is 16bit.
ADC_U16_FACTOR = 1.0 / 65535


class AirQuality:
    """Groove Air Quality Sensor v1.3

    Connect:
      red: either 3.3V or 5V.
      black: ground.
      yellow: one of the ADC pins.
    """
    
    def __init__(self, pin, *, perc: bool = False) -> None:
        self._pin = machine.ADC(pin)
        self._perc = perc
        
    def read(self) -> float:
        """Return sensor value. 0 - good air, 1 - bad air."""
        value = utils.get_adc(self._pin)
        return value * 100 if self._perc else value


_AHTX0_I2CADDR_DEFAULT: int = const(0x38)  # Default I2C address
_AHTX0_CMD_CALIBRATE: int = const(0xE1)  # Calibration command
_AHTX0_CMD_TRIGGER: int = const(0xAC)  # Trigger reading command
_AHTX0_CMD_SOFTRESET: int = const(0xBA)  # Soft reset command
_AHTX0_STATUS_BUSY: int = const(0x80)  # Status bit for busy
_AHTX0_STATUS_CALIBRATED: int = const(0x08)  # Status bit for calibrated

class AHTx0:
    """
    Sensor: Grove - AHT20 I2C Industrial Grade Temperature&Humidity Sensor
    https://wiki.seeedstudio.com/Grove-AHT20-I2C-Industrial-Grade-Temperature&Humidity-Sensor/

    Operating Voltage DC: 2.0V-5.5V
    Measuring Range (humidity): 0 ~ 100% RH
    Temperature Range: -40 ~ + 85 C
    Humidity Accuracy: ± 2% RH (25 C)
    Temperature Accuracy: ± 0.3 C
    Temperature resolution: 0.01 C;
    Humidity resolution : 0.024% RH
    I2C address: 0x38
    
    Example:
        device = sensors.AHTx0(machine.SoftI2C(scl=machine.Pin(1), sda=machine.Pin(0)))
        print(device.temperature)
    
    See:
    - https://github.com/adafruit/Adafruit_AHTX0/blob/master/Adafruit_AHTX0.cpp
    - https://github.com/adafruit/Adafruit_CircuitPython_AHTx0/blob/main/adafruit_ahtx0.py
    """

    def __init__(
        self, i2c_bus, address: int = _AHTX0_I2CADDR_DEFAULT
    ) -> None:
        time.sleep(0.02)  # 20ms delay to wake up
        self.i2c_device = i2c_bus
        self.add = address
        self._buf = bytearray(6)
        self.reset()
        if not self.calibrate():
            raise RuntimeError("Could not calibrate")
        self._temp = None
        self._humidity = None

    def reset(self) -> None:
        """Perform a soft-reset of the AHT"""
        self.i2c_device.writeto(self.add, b'\xba')
        time.sleep(0.02)  # 20ms delay to wake up

    def calibrate(self) -> bool:
        """Ask the sensor to self-calibrate. Returns True on success, False otherwise"""
        buffer = bytearray(3)
        buffer[0] = _AHTX0_CMD_CALIBRATE
        buffer[1] = 0x08
        buffer[2] = 0x00
        self.i2c_device.writeto(self.add, buffer)
        
        while self.status & _AHTX0_STATUS_BUSY:
            time.sleep(0.01)
        if not self.status & _AHTX0_STATUS_CALIBRATED:
            return False
        return True

    @property
    def status(self) -> int:
        """The status byte initially returned from the sensor, see datasheet for details"""
        st = int(self.i2c_device.readfrom(self.add, 1).hex(), 16)
        #print("status: "+hex(st))
        return st

    @property
    def relative_humidity(self) -> float:
        """The measured relative humidity in percent."""
        self._readdata()
        return self._humidity

    @property
    def temperature(self) -> float:
        """The measured temperature in degrees Celsius."""
        self._readdata()
        return self._temp
    
    @property
    def temp_and_humidity(self) -> tuple[float, float]:
        """Gets temp and humidity."""
        self._readdata()
        return self._temp, self._humidity

    def _readdata(self) -> None:
        """Internal function for triggering the AHT to read temp/humidity"""
        buffer = bytearray(3)
        buffer[0] = _AHTX0_CMD_TRIGGER
        buffer[1] = 0x33
        buffer[2] = 0x00
        self.i2c_device.writeto(self.add, buffer)
        
        while self.status & _AHTX0_STATUS_BUSY:
            time.sleep(0.01)
            
        self.i2c_device.readfrom_into(self.add, self._buf)
        
        self._humidity = (
            (self._buf[1] << 12) | (self._buf[2] << 4) | (self._buf[3] >> 4)
        )
        self._humidity = (self._humidity * 100) / 0x100000
        self._temp = ((self._buf[3] & 0xF) << 16) | (self._buf[4] << 8) | self._buf[5]
        self._temp = ((self._temp * 200.0) / 0x100000) - 50


def get_AHT20(scl_pin: int, sda_pin: int):
    """Gets AHT20 device or None if it's not present."""
    if isinstance(scl_pin, int):
        if isinstance(sda_pin, int):
            assert scl_pin - sda_pin == 1    
        scl_pin = machine.Pin(scl_pin)
    if isinstance(sda_pin, int):
        sda_pin = machine.Pin(sda_pin)
    
    i2c_dev = machine.SoftI2C(scl=scl_pin, sda=sda_pin)
    available_devices = i2c_dev.scan()
    if not available_devices:
        return None
    if len(available_devices) == 1:
        return AHTx0(i2c_dev, address=available_devices[0])
    return AHTx0(i2c_dev)


def get_internal_temp() -> float:
    """Gets temp (in C) which is connected to ADC(4)"""
    sensor_temp = machine.ADC(4)
    reading = sensor_temp.read_u16() * 3.3 * ADC_U16_FACTOR 
    temperature = 27 - (reading - 0.706)/0.001721
    return temperature


def get_temp_lm335(pin) -> float:
    """Gets temperature from LM335Z sensor (+- 1C).
    Sensor reports linear temp in kelvins (10mV/K).
    So 2V output is 200K and 0V is 0K. Real range is -40 - 100C, which is 2.33-3.73V.
    Pico ADC reference voltage is 3.3V. So max ADC input (2^16) will refer to 3.3V.
    So ADC will cap at 3.3V which is 330K -> 57C.
    Pico ADC resolution is 12bits which is 0.8mV which is 0.08C.
    Sensor is stable at around 1C.
    Sensor connection:
    left - calibration/not connected
    middle - ADC and 2-3kOmh to 5V
    right - ground
    """
    pin_voltage = utils.get_adc(pin) * 3.3
    temp_K = pin_voltage * 100
    temp_C = temp_K - 273.15
    return temp_C


def get_dht22_temp_humidity(default:tuple[float, float] = (-1, -1), pin: int = 2) -> tuple[float, float]:
    """Gets DFRobot DHT22 sensor module temp and humidity.
    Requires 5V.
    
    Args:
      default: Tuple[float, float]:

    Returns: Tuple[float, float]
    """
    try:
        from DHT22 import DHT22
    except ImportError:
        print('Failed to import DHT22 library.')
        return default
    dht_data = Pin(pin, Pin.IN, Pin.PULL_UP)
    dht_sensor = DHT22(dht_data)
    temp, hum = dht_sensor.read()
    if temp is None:
        print("DHT22 sensor error.")
        return default
    return temp, hum


def get_moisture_v1(pin) -> float:
    """Read Moisture sensor value and return in range 0-1.
    
    This is for DFRobot SEN0193, capacitive moisture sensor:
    https://wiki.dfrobot.com/Capacitive_Soil_Moisture_Sensor_SKU_SEN0193
    
    Operating Voltage: 3.3 ~ 5.5 VDC
    Output Voltage: 0 ~ 3.0VDC
    Operating Current: 5mA
    Interface: PH2.0-3P
    
    Calibration values (16bit):
    Air: 51000
    Water to the top: 25000
    Water to mid range: 25500

    Args:
      pin: can be int, Pin or ADC object.

    Returns:
      0 - lowest moisture (i.e. air),
      1 - highest moisture (i.e. water).
    """
    AIR_VALUE = 51000  # Translates to 0%
    WATER_VALUE = 25500  # Translates to 100%
    return utils.get_adc(pin, AIR_VALUE, WATER_VALUE, clip=True)


def get_moisture_v2(pin, supply_5v: bool = False) -> float:
    """Read Moisture sensor value and return in range 0-1.
    
    This is for DFRobot SEN0114, resistance moisture sensor:
    https://wiki.dfrobot.com/Moisture_Sensor__SKU_SEN0114_
    
    Power supply: 3.3v or 5v
    Output voltage signal: 0~4.2v. Gives 4.2V with 5V supply and 2.1V with 3.3V supply.
    Current: 35mA
    
    Calibration values (16bit):
    Air: 320
    Water to the top: 40000-42500, depending on sensor

    Args:
      pin: can be int, Pin or ADC object.
      supply_5v: flag whether the power supply is 5v. Assume 3.3V otherwise.

    Returns:
      0 - lowest moisture (i.e. air),
      1 - highest moisture (i.e. water).
    """
    AIR_VALUE = 400 if supply_5v else 320 # Translates to 0%
    WATER_VALUE = 65535 if supply_5v else 41000  # Translates to 100%
    return utils.get_adc(pin, AIR_VALUE, WATER_VALUE, clip=True)
