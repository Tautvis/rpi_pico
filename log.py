"""Tiny logger"""

# Where to log.
_destination = print
# Available log levels.
_LOG_LEVELS = {'ALL': 40, 'DEBUG': 30, 'INFO': 20, 'WARN': 10, 'ERROR': 0}
# Log level.
_level = _LOG_LEVELS['ALL']

def set_level(new_level) -> None:
    """Sets new log level. Either string or int."""
    if isinstance(new_level, int):
        _level = new_level
    elif isinstance(new_level, str):
        if new_level not in _LOG_LEVELS:
            print(f'log.set_level: Unknown log level: {new_level}')
        _level = _LOG_LEVELS[new_level]
    else:
        print(f'log.set_level: Level must be int/str. Received: {new_level}')
        
        
def debug(msg: str) -> None:
    if _level >= 30:
        _destination(msg)
