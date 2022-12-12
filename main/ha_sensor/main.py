import machine
import time
import utils, sensors, log, wlan, comms
from machine import Timer
from machine import Pin
#machine.reset()

# Config
export_period_s = 1 * 60
topic = 'home/bathroom'
temp_offset = -0.7

    
try:
    utils.blink(2)
    wlan.connect(60*60)
    utils.blink(1)

    comms = comms.Comms(keepalive=False, topic=topic)

    # air_q_sensor = sensors.AirQuality(26, perc=True)
    aht20 = sensors.get_AHT20(1, 0)
    log.debug('Starting sensor loop')
    while(True):
        log.debug('Reading and exporting data.')
        # air_q = air_q_sensor.read()
        internal_temp = sensors.get_internal_temp()
        #temp, humi = sensors.get_dht22_temp_humidity(pin=2)
        temp, humi = aht20.temp_and_humidity

        results = {
            'timestamp': int(time.time()),
            # 'air_quality': round(air_q, 1),
            'internal_temp': round(internal_temp, 1)
            }
        if temp > 0:
            results['temperature'] = round(temp + temp_offset, 1)
        if humi > 0:
            results['humidity'] = round(humi, 1)
        
        utils.blink(2, end_off=True)
        comms.send(topic, results)
        
        time.sleep(export_period_s)
    
except Exception as e:
    try:
        comms.disconnect()
    except:
        log.debug('Failed to disconnect')
    log.debug(e)
    utils.blink_error()

# timed_task = Timer(period=5000, mode=Timer.ONE_SHOT, callback=lambda t:print(1))
# timed_task.init(period=2000, mode=Timer.PERIODIC, callback=lambda t:print(2))
