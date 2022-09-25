"""Communication to MQTT broker."""
import secrets
import log
import json
# import upip
# upip.install("umqtt.simple")
from umqtt.simple import MQTTClient

# JSON fields
# ts: timestamp of the measurment. Unix milles since epoch.
# temperature: temperature
# temp_sensor_type: {}
# humidity: Humidity if available.
# air_quality: Percentage of polution.


class Comms:
    def __init__(self, name: str = '', keepalive: bool = False):
        """Create comms client.

        Args:
          name: name of the client. Can be None with QoS=0 and publish only.
        """
        self.name = name
        self.keepalive = keepalive
        self.client = MQTTClient(name, secrets.mqtt_broker_address, port=secrets.mqtt_broker_port,
                                 user=secrets.mqtt_user, password=secrets.mqtt_password,
                                 keepalive=3600)
        # Set last will message here.
        if self.keepalive:
            self.client.connect()
        
    def send(self, topic: str, msg: str, qos: int = 0) -> None:
        """Send message.
        
        Args:
            topic: mqtt topic to send message to.
            msg: message to send, can be string or dict.
            qos: Quality of Service: 0-at most once, 1-al least once, 2-exatly once (not implemented).
        """
        if self.keepalive:
            try:
                self.client.ping()
            except OSError:
                log.debug('Reconnecting to MQTT broker.')
                self.client.connect()
        else:
            self.client.connect()
    
        assert isinstance(msg, (str, dict)), f'Message of type {type(msg)} is not supported.'

        if isinstance(msg, dict):
            msg = json.dumps(msg)
            
        # Send message.
        self.client.publish(topic, msg, qos=qos)
        
        if not self.keepalive:
            self.client.disconnect()
        