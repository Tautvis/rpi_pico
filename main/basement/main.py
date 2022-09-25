import time
import utils
import machine
from machine import Pin
from machine import Timer

SEC = 1000
MIN = 60 * SEC
HEADER = 'timestamp,temperature,humidity\n'
FILENAME = 'atmo.csv'

led = utils.get_led()
rtc = machine.RTC()

# Add CSV header if file doesn't exist yet.
if not utils.file_exists(FILENAME):
    with open(FILENAME, 'a') as fout:
        fout.write(HEADER)
        
led.on()
time.sleep_ms(100)
led.off()        
time.sleep_ms(200)
led.on()
time.sleep_ms(100)
led.off()


def export_temp(timer):
    led.on()
    temp, hum = utils.get_dht22_temp_humidity()
    
    timestamp = rtc.datetime()
    timestring = "%04d-%02d-%02d %02d:%02d:%02d" % (timestamp[0:3] + timestamp[4:7])
    
    with open(FILENAME, 'a') as fout:            
        fout.write(f'{timestring},{temp},{hum}\n')
    
    print(f'{timestring}: {temp}C, {hum}%')
    led.off()

timer = Timer(period=10*MIN, mode=Timer.PERIODIC, callback=export_temp)
    
    

# while True:
#     temp, hum = utils.get_dht22_temp_humidity()
#     print(f'{temp}C, {hum}%')
#     led.toggle()
#     time.sleep(0.5)
   
#try:
#    while True:
#        pass
#        #led.toggle()
#        #time.sleep(0.5)
#except:
#    timer.deinit()
        
