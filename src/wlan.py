import network
import secrets
import utime
import log

WLAN = None


def connect(max_wait: int = 30) -> None:
    """Connect to Wi-Fi and sets time."""
    global WLAN
    if WLAN and WLAN.active():
        log.debug('Already connected to wifi.')
        return
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
    log.debug('Connected to Wifi.')
    status = wlan.ifconfig()
    log.debug('Wifi ip: ' + status[0])
    WLAN = wlan
