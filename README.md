# Raspberry Pi PicoW tools

## Setup

1. Install Thonny and set up Pico.
1. Update secrets.py with your wifi ssid/password.
1. Upload all libraries to Pico root.
1. Run one time setup to install 3rd party libs (i.e. umqtt.simple):
    ```python
    import wlan, setup
    wlan.connect()
    setup.setup()
    ```
1. Select on of the main.py form main/ folder depending on the task and uplaod to pico root.
1. You're all set up.
