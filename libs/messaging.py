# all of the publish and subscript messaging commands

# http://www.steves-internet-guide.com/client-connections-python-mqtt/

import paho.mqtt.client as paho
import json
import time
import logging

logger = logging.getLogger(__name__)

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

class Messaging:

    def __init__(self, server=None, port=None) -> None:
        self.connected = False
        self.client = None
        self.topic = None
        self.topic_handler = None
        self.server =  server
        self.port =  port


    # ----------------------------------------------------------------------------
    def on_disconnect(self, client, userdata, rc):
        """
        """
        print("on disconnect")
        if rc != 0:
            print("Unexpected MQTT disconnection. Will auto-reconnect")


    def on_disconnect_retry(self, client, userdata, rc):
        logger.info("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            logger.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                self.client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        logger.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

    # ----------------------------------------------------------------------------


    def on_connect(self, client, userdata, flags, reason_code, properties):
        """
        """
        if reason_code == 0:
            logger.info(f"Connected to MQTT server: {self.server}:{self.port}")
            self.client.subscribe(self.topic, qos=1)
        else:
            logger.debug("Failed to connect, return code: {}".format(reason_code))


    # ----------------------------------------------------------------------------
    def on_message(self, client, userdata, message):
        """
        """
        # Identify topic and call appropriate handler function
        # we will ignore the user data and pull out the payload
        # for this usecase not much else is needed

        logger.debug( f"topic: {message.topic} data:{message.payload.decode()}")
        if self.topic_handler:
            self.topic_handler(topic=message.topic, data=json.loads(message.payload.decode()))


    # ----------------------------------------------------------------------------
    # pass topic handlers if we are in a subscription kinda mood,
    # will then loop forever waiting for topics to be pubished


    def connect(self, topic=None, topic_handler=None):
        """
        """

        if topic != None:
            self.topic = topic

        self.client = paho.Client(paho.CallbackAPIVersion.VERSION2)
        # if we need a username and password
        # client.username_pw_set(server, pwd)

        # keep alive is 300s
        if self.client.connect(self.server, self.port, 300) != 0:
            logger.error(f"Couldn't connect to the MQTT server: {self.server}:{self.port}")
            self.connected = False
        else:
            self.connected = True

        # put these after the connect, so that they subscribe after re-connecting
        self.client.on_disconnect = self.on_disconnect
        self.topic_handler = topic_handler
        self.client.on_connect = self.on_connect

        # now to the subscription loop if needed
        if topic_handler:
            self.client.on_message = self.on_message
            self.client.loop_forever()


    # ----------------------------------------------------------------------------
    def publish(self, subtopic, data={}):
        """
        """

        # attempt a reconnect if needed
        if not self.connected:
            self.connect()

        if self.connected:
            self.client.publish(f"{subtopic}",  json.dumps(data))


    # ----------------------------------------------------------------------------
    def client_disconnect(self):
        """
        """
        if self.connected:
            self.client.disconnect()


