import machine
import socket
import time
import utils, sensors, log, wlan

from machine import Pin
#machine.reset()

utils.blink(2)

led = utils.get_led()

wlan.connect()

default_htmp_values = {'led_state': 'n/a', 'temp': 'n/a', 'humidity': 'n/a', 'air_q': 'n/a'}
html = """<!DOCTYPE html>
    <html>
        <head> <title>Pico W</title> </head>
        <body> <h1>Pico W</h1>
            <p>Hello World</p>
            <p> LED state: {led_state}. </p>
            <p> Current weather: {temp:3.1f}C, {humidity:3.1f}% humidity. </p>
            <p> Air quality (0% - best): {air_q:.2f}% </p>
            <p>
            <a href='/light/on'>Turn Light On</a>
            </p>
            <p>
            <a href='/light/off'>Turn Light Off</a>
            </p>
            <br>
        </body>
    </html>
"""

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.bind(addr)
s.listen(1)

print('listening on', addr)

air_q_sensor = sensors.AirQuality(28, perc=True)

# Listen for connections
while True:
    try:
        cl, addr = s.accept()
        print('client connected from', addr)
        request = cl.recv(1024)
        print(request)

        request = str(request)
        led_on = request.find('/light/on')
        led_off = request.find('/light/off')
        print( 'led on = ' + str(led_on))
        print( 'led off = ' + str(led_off))


        stateis = 'Unknown'
        if led_on != -1:
            print("led on")
            led.value(1)
            stateis = "LED is ON"

        if led_off != -1:
            print("led off")
            led.value(0)
            stateis = "LED is OFF"
        
        temp, humi = sensors.get_dht22_temp_humidity()
        if temp <= 0:
            temp = sensors.get_internal_temp()
            humi = -1
        air_q = air_q_sensor.read()
        response = html.format(led_state=stateis, temp=temp, humidity=humi,
                               air_q=air_q, **default_htmp_values)

        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        cl.send(response)
        cl.close()

    except OSError as e:
        cl.close()
        print('connection closed')