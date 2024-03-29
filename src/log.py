"""Tiny logger."""
import utils
import io
import os
import time
import sys

# Where to log.
_destination = print
# Available log levels.
_LOG_LEVELS = {'ALL': 40, 'DEBUG': 30, 'INFO': 20, 'WARN': 10, 'ERROR': 0, 'OFF': -1}
# Log level.
_level = _LOG_LEVELS['ALL']
# Logger settings.
_min_free_flash_mem = 12*1024
_LOG_DIR = '/logs'

def set_level(new_level) -> None:
    """Set new log level. Either string or int."""
    if isinstance(new_level, int):
        _level = new_level
    elif isinstance(new_level, str):
        if new_level not in _LOG_LEVELS:
            print(f'log.set_level: Unknown log level: {new_level}')
        _level = _LOG_LEVELS[new_level]
    else:
        print(f'log.set_level: Level must be int/str. Received: {new_level}')

def error(msg: str) -> None:
    if _level >= 0:
        _destination(msg)
        log_to_fs(msg)

def warn(msg: str) -> None:
    if _level >= 10:
        _destination(msg)

def info(msg: str) -> None:
    if _level >= 20:
        _destination(msg)
        
def debug(msg: str) -> None:
    if _level >= 30:
        _destination(msg)
        
def trace(msg: str) -> None:
    if _level >= 40:
        _destination(msg)
        
# Log level functions.
LOG_FUNCTIONS = {
    'ALL': trace,
    'DEBUG': debug,
    'INFO': info,
    'WARN': warn,
    'ERROR': error,
    'OFF': lambda msg: None
}

def log_to_fs(data: str, append_dt: bool = True) -> None:
    """
    """
    stats = utils.get_free_memory()
    if stats.free_memory < _min_free_flash_mem:
        return

    # Log files: /logs/log_2023_04_24.txt
    if not utils.dir_exists(_LOG_DIR):
        os.mkdir(_LOG_DIR)
    dt = time.gmtime()
    with io.open(f'{_LOG_DIR}/log_{dt[0]}_{dt[1]}_{dt[2]}.txt', 'a') as fout:
        if append_dt:
            timestring = '%04d-%02d-%02d %02d:%02d:%02d ' % dt[0:6]
            fout.write(timestring)
        if isinstance(data, Exception):
            sys.print_exception(data, fout)
        else:
            fout.write(data)
        fout.write('\n')
