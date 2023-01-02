"""SCD30 sensor lib for Raspberry Pi Pico or Pico W.

Adapted from cpp library: https://github.com/Seeed-Studio/Seeed_SCD30
And full Python library: https://github.com/RequestForCoffee/scd30

SCD30 communicates in 2-byte words.
"""
import machine, utils, time
from micropython import const
import struct


_SCD30_CONTINUOUS_MEASUREMENT: int = const(0x0010)
_SCD30_SET_MEASUREMENT_INTERVAL: int = const(0x4600)
_SCD30_GET_DATA_READY: int = const(0x0202)
_SCD30_READ_MEASUREMENT: int = const(0x0300)
_SCD30_STOP_MEASUREMENT: int = const(0x0104)
_SCD30_AUTOMATIC_SELF_CALIBRATION: int = const(0x5306)
_SCD30_SET_FORCED_RECALIBRATION_FACTOR: int = const(0x5204)
_SCD30_SET_TEMPERATURE_OFFSET: int = const(0x5403)
_SCD30_SET_ALTITUDE_COMPENSATION: int = const(0x5102)
_SCD30_READ_SERIALNBR: int = const(0xD033)
_SCD30_SET_TEMP_OFFSET: int = const(0x5403)

_SCD30_POLYNOMIAL: int = const(0x31)  # P(x) = x^8 + x^5 + x^4 + X^0 = 100110001


def interpret_as_float(integer: int) -> float:
    return struct.unpack('!f', struct.pack('!I', integer))[0]


def int_to_bytes(integer: int) -> bytes:
    return int.to_bytes(integer, 2, 'big')


def _first(values: list) -> int:
    """Gets first value or None."""
    if not values:
        return None
    return values[0]


class SCD30:
    """Groove CO2 Sensor SCD30
    
    Connect:
      red: either 3.3V or 5V.
      black: ground.
      I2C: pin 2 and 3 (i2c 1st hardware slot).
    """

    def __init__(self, sda_pin: int = 2, scl_pin: int = 3, logger = lambda msg: None) -> None:
        """
        Args:
          logger: optional logger function. E.g. 'log.trace'.
        """
        self.address = 0x61
        self._default_readings = [None, None, None]
        self.log = logger
        # Using hardware I2C as software one didn't work?
        self.i2c = machine.I2C(id=1, sda=machine.Pin(sda_pin), scl=machine.Pin(scl_pin))
        
    def initialize(self) -> None:
        pass

    def is_data_ready(self) -> bool:
        """Checks if sensor data is ready to be read."""
        rval = self._send_command(_SCD30_GET_DATA_READY)
        return bool(_first(rval))

    def get_serial_number(self) -> int:
        """Gets serial number."""
        return _first(self._send_command(_SCD30_READ_SERIALNBR))

    def get_measurement_interval(self) -> int:
        """Gets measurement interval in seconds."""
        return _first(self._send_command(_SCD30_SET_MEASUREMENT_INTERVAL))

    def set_measurement_interval(self, interval: int) -> int:
        """Sets measurement interval in seconds."""
        if not 2 <= interval <= 1800:
            raise ValueError('Interval must be in the range [2; 1800] (sec)')
        rval = self._send_command(_SCD30_SET_MEASUREMENT_INTERVAL, arguments=interval)
        return _first(rval)

    def is_auto_self_calibration(self) -> int:
        """Gets the automatic self-calibration status."""
        return _first(self._send_command(_SCD30_AUTOMATIC_SELF_CALIBRATION))

    def set_auto_self_calibration(self, enable: bool) -> None:
        self._send_command(_SCD30_AUTOMATIC_SELF_CALIBRATION, 0, arguments=int(enable))

    def start_periodic_measurement(self, atm_presure: int = 0) -> None:
        if atm_presure and not 700 <= atm_presure <= 1400:
            raise ValueError(f'Atmosphere pressure should be in range 700-1400 or off (zero). Received {atm_presure}.')
        self._send_command(_SCD30_CONTINUOUS_MEASUREMENT, 0, atm_presure)

    def stop_measurement(self) -> None:
        self._send_command(_SCD30_STOP_MEASUREMENT, 0)

    def get_temperature_offset(self) -> float:
        """Gets temperature offset in Celsius."""
        # Sensor operates in Celsius percentiles (0.01C per 1 int).
        # Thus 5.6C would be 560 offset.
        rval = self._send_command(_SCD30_SET_TEMP_OFFSET, 1)
        return _first(rval)/100.0

    def set_temperature_offset(self, offset: float) -> None:
        """Sets temperature offset to given value in Celsius."""
        self._send_command(_SCD30_SET_TEMP_OFFSET, 0, arguments=int(100*offset))

    def get_atmosphere_presure(self) -> int:
        """Gets atmosphere presure set on sensor."""
        return _first(self._send_command(_SCD30_SET_ALTITUDE_COMPENSATION, 1))

    def set_atmosphere_presure(self, atm_presure: int) -> int:
        """Sets atmosphere presure. Zero - turns off compensation."""
        if atm_presure and not 700 <= atm_presure <= 1400:
            raise ValueError(f'Atmosphere pressure should be in range 700-1400 or off (zero). Received {atm_presure}.')
        return _first(self._send_command(_SCD30_SET_ALTITUDE_COMPENSATION, 1, atm_presure))

    def get_data(self) -> tuple[float, float, float]:
        """Reads CO2, temperature and humidity from sensor.
        Must be called when #is_data_ready() is True or use #get_data_blocking().
        Returns:
          CO2, temperature, humidity.
        """
        data = self._send_command(_SCD30_READ_MEASUREMENT, num_response_words=6)

        if data is None or len(data) != 6:
            self.log(f'Failed to read measurement, received: {data}')
            return self._default_readings

        co2_ppm = interpret_as_float((data[0] << 16) | data[1])  # First word is CO2.
        temp_celsius = interpret_as_float((data[2] << 16) | data[3])  # Second word is temp.
        rh_percent = interpret_as_float((data[4] << 16) | data[5])  # Third word is relative humidity.
        return (co2_ppm, temp_celsius, rh_percent)

    def get_data_blocking(self, max_wait: float = 0.0) -> tuple[float, float, float]:
        """Waits until ready and then reads CO2, temperature and humidity.

        Args:
          max_wait: max wait time in seconds.
        """
        start_ticks = time.ticks_ms()
        while not self.is_data_ready():
            # Try reading 5 times per second.
            time.sleep_ms(200)
            if max_wait > 0 and max_wait < time.ticks_diff(time.ticks_ms(), start_ticks) / 1000.0:
                return self._default_readings

        return self.get_data()

    def _validate_2byte(self, word: int, msg: str = 'arg') -> None:
        """Asserts that word is 2-byte"""
        assert 0 <= word <= 0xFFFF, f'{msg} outside valid two-byte word range: {word}'

    def _crc8(self, word: int) -> int:
        """Computes the CRC-8 checksum as per the SCD30 interface description.
        Parameters:
            word: two-byte integer word value to compute the checksum over.
        Returns:
            single-byte integer CRC-8 checksum.
        Polynomial: x^8 + x^5 + x^4 + 1 (0x31, MSB)
        Initialization: 0xFF
        Algorithm adapted from:
        https://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
        """
        self._validate_2byte(word, "word")
        rem = 0xFF
        for byte in int_to_bytes(word):
            rem ^= byte
            for _ in range(8):
                if rem & 0x80:
                    rem = (rem << 1) ^ _SCD30_POLYNOMIAL
                else:
                    rem = rem << 1
                rem &= 0xFF
        return rem

    def _send_command(self, command: int, num_response_words: int = 1,
                      arguments: list = ()) -> list[int]:
        """Sends the provided I2C command and reads out the results.
        Parameters:
            command: the 2-byte command code, e.g. 0x0010.
            num_response_words: number of 2-byte words in the result.
            arguments: list, tuple or single number. Must be convertable to 2-byte word.
        Returns:
            list of num_response_words 2-byte int values from the sensor.
        """
        self._validate_2byte(command, 'command')

        raw_message = [int_to_bytes(command)]
        if not isinstance(arguments, (tuple, list)):
            arguments = [arguments]
        for argument in arguments:
            self._validate_2byte(argument, 'argument')
            raw_message.append(int_to_bytes(argument))
            raw_message.append(int.to_bytes(self._crc8(argument), 1, 'big'))

        self.log(f'Sending message: {raw_message}')
        n_acks = self.i2c.writevto(self.address, raw_message)
        # Expected 2 acks for each 2-byte word and 1 ack for CRC 1-byte check.
        n_expected_acks = 2 if not arguments else (2*len(raw_message) - 1)
        if n_acks != n_expected_acks:
            self.log(f'Not full message was ack\'ed. Received {n_acks}/{n_expected_acks} acks.')

        # The interface description suggests a >3ms delay between writes and
        # reads for most commands.
        time.sleep_ms(5)

        if num_response_words == 0:
            return []

        # Data is returned as a sequence of num_response_words 2-byte words
        # (big-endian), each with a CRC-8 checksum:
        # [MSB0, LSB0, CRC0, MSB1, LSB1, CRC1, ...]
        raw_response = self.i2c.readfrom(self.address, 3 * num_response_words)
        response = []
        for i in range(num_response_words):
            # word_with_crc contains [MSB, LSB, CRC] for the i-th response word
            word_with_crc = raw_response[3*i: 3*i + 3]
            word = int.from_bytes(word_with_crc[:2], 'big')
            response_crc = word_with_crc[2]
            computed_crc = self._crc8(word)
            if response_crc != computed_crc:
                self.log(f'CRC verification for word {word} failed: received {response_crc}, computed {computed_crc}.')
                return []
            response.append(word)

        self.log(f'Response: {response}')
        return response
