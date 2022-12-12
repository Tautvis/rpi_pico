import machine
import sys
from machine import Pin
import time
import os



def is_picow() -> bool:
    """Returns wheter it's running Pico or Pico W"""
    pico_name   = 'Raspberry Pi Pico with RP2040'
    pico_w_name = 'Raspberry Pi Pico W with RP2040'
    name = sys.implementation._machine
    assert name in {pico_name, pico_w_name}, f'Unknown machine name: {name}'
    return name == pico_w_name

    
def is_adc_pin(pin: int) -> bool:
    """Returns whether pin is capable opf ADC."""
    return pin == 26 or pin == 27 or pin == 28


def get_adc(pin, min_val: int = 0, max_val: int = 65535, clip: bool = False) -> float:
    """Gets calibrated ADC value in range 0-1.

    Calibration means that the Pin output doesn't use the whole 0-65535 range.
    
    Args:
      pin: can be int, Pin or ADC object.
      min_val: minimum expected value - will return 0.
      max_val: maximum expected value - will return 1.
      clip: Whether to clip to [0-1] range.
    """
    if isinstance(pin, (int, Pin)):
        pin = machine.ADC(pin)
    value = pin.read_u16()
    value = (value - min_val) / (max_val - min_val)
    if clip:
        value = max(0, min(1, value))
    return value

read_adc = get_adc


def get_led() -> machine.Pin:
    """Gets Pin for on-board LED for Pico W or Pico."""
    if is_picow():
        return Pin('LED', Pin.OUT)
    else:
        return Pin(25, Pin.OUT)
    

def blink(n:int = 1, delay_ms:int = 100, end_off:bool = None, pin:machine.Pin = None) -> None:
    """Blinks n times. Stops in a given position.

    Args:
      n: n times to blink.
      delay_ms: ms to wait between toggeles. Total time is 2 * n * delay_ms.
      end_off: wheter to force the led to off at the end.
      pin: LED pin. Defaults to on board LED.
    """
    if pin is None:
        pin = get_led()
        
    for i in range(n):
        pin.toggle()
        time.sleep_ms(delay_ms)
        pin.toggle()
        time.sleep_ms(delay_ms)
        
    if end_off is not None and end_off is True:
        pin.off()


def blink_pattern(pattern: list[int], duration: float = 1.0, pin:machine.Pin = None) -> None:
    """Blink given pattern in given duration

    Args:
      pattern: list of 1s and 0s.
      duration: duration to blink the pattern out (in seconds).
    """
    if not pattern: return
    if pin is None:
        pin = get_led()
        
    step_duration_us = int(1_000_000 * duration / len(pattern))
    start = time.ticks_us()
    for i, state in enumerate(pattern, 1):
        pin(state)
        time.sleep_us(time.ticks_diff(start + i * step_duration_us, time.ticks_us()))
        
    pin.off()

        
def blink_error() -> None:
    """Continuously blink urecoverable error pattern on the board LED."""
    error_pattern = [1,0,0,1,1,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0]
    while(True):
        blink_pattern(error_pattern, 2)
    

def file_or_dir_exists(filename: str) -> bool:
    try:
        os.stat(filename)
        return True
    except OSError:
        return False
        
def dir_exists(filename: str) -> bool:
    try:
        return (os.stat(filename)[0] & 0x4000) != 0
    except OSError:
        return False
        
def file_exists(filename: str) -> bool:
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False
    
    