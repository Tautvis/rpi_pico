import network
import secrets
import utime
import log

def connect(max_wait: int = 30) -> None:
    """Connects to wifi and sets time."""
    log.debug('Connecting to wifi . . .')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(secrets.ssid, secrets.password)
    
    for i in range(1, max_wait+1):
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        log.debug(f'({i}/{max_wait}s) . . . waiting for wifi connection...')
        utime.sleep(1)

    if wlan.status() != network.STAT_GOT_IP:
        raise RuntimeError(f'Network connection failed. Status: {wlan.status()}. wlan: {wlan}.')
    else:
        log.debug('Connected to Wifi.')
        status = wlan.ifconfig()
        log.debug('Wifi ip: ' + status[0])
