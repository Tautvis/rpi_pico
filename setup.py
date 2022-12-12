"""Initial Raspberry Pi Pico setup"""
import mip
import wlan


def setup():
    print('Starting set up.')
    wlan.connect()
    mip.install('umqtt.simple')
    print('Set up complete.')
    
    
if __name__ == '__main__':
    setup()