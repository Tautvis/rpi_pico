import sys
import machine
from machine import Pin
import time
import os
import gc
from collections import namedtuple

# Flash memory stats in bytes.
FlashStats = namedtuple('FlashStats', ('total_memory', 'free_memory', 'used_memory'))

def is_picow() -> bool:
    """Return whether it's running Pico or Pico W"""
    pico_name   = 'Raspberry Pi Pico with RP2040'
    pico_w_name = 'Raspberry Pi Pico W with RP2040'
    name = sys.implementation._machine
    assert name in {pico_name, pico_w_name}, f'Unknown machine name: {name}'
    return name == pico_w_name

    
def is_adc_pin(pin: int) -> bool:
    """Return whether pin is capable opf ADC."""
    return pin == 26 or pin == 27 or pin == 28


def get_adc(pin, min_val: int = 0, max_val: int = 65535, clip: bool = False) -> float:
    """Get calibrated ADC value in range 0-1.

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
        value = max(0.0, min(1.0, value))
    return value


read_adc = get_adc


def get_led() -> machine.Pin:
    """Get Pin for on-board LED for Pico W or Pico."""
    if is_picow():
        return Pin('LED', Pin.OUT)
    else:
        return Pin(25, Pin.OUT)
    

def blink(n:int = 1, delay_ms:int = 100, end_off:bool = None, pin:machine.Pin = None) -> None:
    """Blink n times. Stops in a given position.

    Args:
      n: n times to blink.
      delay_ms: ms to wait between toggles. Total time is 2 * n * delay_ms.
      end_off: whether to force the LED to off at the end.
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
    """Continuously blink unrecoverable error pattern on the board LED."""
    error_pattern = [1,0,0,1,1,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0]
    while True:
        blink_pattern(error_pattern, 2)


def clip(value, min_val=None, max_val=None):
    """Clip value to a range and cast to the same type."""
    dtype = type(value)
    if max_val is not None:
        value = min(max_val, value)
    if min_val is not None:
        value = max(min_val, value)
    return dtype(value)


def fn_avg(fn, n_avg: int = 3, delay_ms: int = 0):
    """Run function n_avg times with delay_ms and return average value.
    """
    n_avg = 3
    acc = None
    for i in range(n_avg):
        data = fn()
        if acc is None:
            if isinstance(data, tuple):
                data = list(data)
            acc = data
        else:
            if isinstance(acc, list):
                for j, _d in enumerate(data):
                    acc[j] += _d
            else:
                acc += data
        if delay_ms > 0:
            time.sleep_ms(delay_ms)
    if isinstance(acc, list):
        return [d/n_avg for d in acc]
    else:
        return acc / n_avg


def init_gc(fraction: float = 0.9) -> None:
    """Initialize GC."""
    total_memory = gc.mem_alloc() + gc.mem_free()
    threshold = int(total_memory * total_memory)
    gc.threshold(threshold)
    gc.enable()
    

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


def get_free_memory() -> FlashStats:
    """Get internal storage stats.

    See https://docs.micropython.org/en/latest/library/os.html#os.statvfs.
    """
    stats = os.statvfs('/')
    f_frsize = stats[1]
    f_blocks = stats[2]
    f_bfree = stats[3]
    total_memory = f_frsize * f_blocks
    free_memory = f_frsize * f_bfree
    return FlashStats(total_memory, free_memory, total_memory-free_memory)



    
    