"""Initial Raspberry Pi Pico setup"""
import upip
import wlan


def setup():
    print('Starting set up.')
    wlan.connect()
    upip.install('umqtt.simple')
    print('Set up complete.')
    
    
if __name__ == '__main__':
    setup()