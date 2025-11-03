#!/usr/bin/env python3

"""mqtt2jsonl

Allows the recording and replay of MQTT messages sent to a particular topic.
The messages are recorded to a JSONL (https://jsonlines.org/) file and the
delay between messages is also recorded so that they can be replayed at the
same rate they were captured, though this can be over-riden if required.

"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import jsonlines
import paho.mqtt.client as paho

logger = logging.getLogger(__name__)

MQTT_SERVER = "localhost"
MQTT_PORT = 1883

# handy globals
mqtt = None
jsonl_file = None
time_since = 0

# ----------------------------------------------------------------------------

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
        self.server = server
        self.port = port

    # ----------------------------------------------------------------------------
    def on_disconnect(self, client, userdata, rc):
        """ """
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
        """ """
        if reason_code == 0:
            logger.info(f"Connected to MQTT server: {self.server}:{self.port}")
            self.client.subscribe(self.topic, qos=1)
        else:
            logger.debug("Failed to connect, return code: {}".format(reason_code))

    # ----------------------------------------------------------------------------
    def on_message(self, client, userdata, message):
        """ """
        # Identify topic and call appropriate handler function
        # we will ignore the user data and pull out the payload
        # for this usecase not much else is needed

        logger.debug(f"topic: {message.topic} data:{message.payload.decode()}")
        if self.topic_handler:
            self.topic_handler(
                topic=message.topic, data=json.loads(message.payload.decode())
            )

    # ----------------------------------------------------------------------------
    # pass topic handlers if we are in a subscription kinda mood,
    # will then loop forever waiting for topics to be pubished

    def connect(self, topic=None, topic_handler=None):
        """ """

        if topic != None:
            self.topic = topic

        self.client = paho.Client(paho.CallbackAPIVersion.VERSION2)
        # if we need a username and password
        # client.username_pw_set(server, pwd)

        # keep alive is 300s
        if self.client.connect(self.server, self.port, 300) != 0:
            logger.error(
                f"Couldn't connect to the MQTT server: {self.server}:{self.port}"
            )
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
        """ """

        # attempt a reconnect if needed
        if not self.connected:
            self.connect()

        if self.connected:
            self.client.publish(f"{subtopic}", json.dumps(data))

    # ----------------------------------------------------------------------------
    def client_disconnect(self):
        """ """
        if self.connected:
            self.client.disconnect()


# ----------------------------------------------------------------------------


def signal_handler(sig, frame):
    """basic signal handler for tidy exit without lots of messages"""

    logger.info("You pressed Ctrl+C!")

    sys.exit(0)


# ----------------------------------------------------------------------------
def setLogLevel(loglevel):
    logging.basicConfig(
        format="%(asctime)s %(module)s(%(funcName)s:%(lineno)d) %(levelname)s : %(message)s",
        level=loglevel,
    )


# ----------------------------------------------------------------------------
def time_msecs():
    return round(time.time() * 1000)


# ----------------------------------------------------------------------------
def record_cb(topic, data):
    global time_since
    now = time_msecs() - time_since
    # update the time
    time_since = time_msecs()

    # append JSON
    with jsonlines.open(jsonl_file, mode="a") as writer:
        # write just one line
        writer.write({"time_delay": now, "topic": topic, "data": data})
        writer.close()


# ----------------------------------------------------------------------------
def record(host, port, file, topic, overwrite=False):
    """record
    record a MQTT session

    Args:
      host      (str): MQTT hostname or IP address
      port      (int): MQTT server port number
      file      (str): JSONL file to read messages from
      topic     (str): MQTT topic to listen to, wildcards allowed
      overwrite (int): Force overwrite of any existing JSONL file

    Returns: nothing
    """

    global jsonl_file
    global time_since
    logger.info(f"Starting to record {host}:{port} for {topic} into {file}")

    if not len(file):
        print(f"Error: no JSONL file provided")
        sys.exit(1)

    if os.path.isfile(file):
        if overwrite:
            os.remove(file)
        else:
            print(
                f"To overwrite the existing '{file}', you need to provide the force option"
            )
            sys.exit(1)

    jsonl_file = file
    mqtt = Messaging(server=host, port=port)
    # set the time we started, so we can offset from that
    time_since = time_msecs()

    print("Ready to record, press CTRL+C when you want to stop")
    mqtt.connect(topic, record_cb)


# ----------------------------------------------------------------------------
def replay(host, port, file, delay):
    """
    replay a previously saved MQTT session

    Args:
      host  (str): MQTT hostname or IP address
      port  (int): MQTT server port number
      file  (str): JSONL file to read messages from
      delay (int): override delays given against each message, if > 0

    Returns: nothing
    """

    if not len(file) or not os.path.isfile(file):
        print(f"Error: no JSONL file provided")
        sys.exit(1)

    mqtt = Messaging(server=host, port=port)

    if delay:
        print(f"Replaying with {delay}ms delay")
    else:
        print("Replaying with recorded delay")
    with jsonlines.open(file) as reader:
        for obj in reader:
            logger.info(f"{obj['topic']}")
            mqtt.publish(obj["topic"], obj["data"])
            delay_time = obj["time_delay"] if delay == 0 else delay
            time.sleep(delay_time / 1000)


def main():
    # handle expected signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # set default log level to WARNING but if environment variable is available use that
    LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
    logger.info("Started")

    parser = argparse.ArgumentParser(
        description=f"Either record or replay MQTT via a JSONL file"
    )
    parser.add_argument(
        "cmd",
        type=str,
        help="Command to perform against the MQTT topic queue, 'record' or 'replay'",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        # the following makes it a boolean flag
        action="store_true",
        help="Increase level of logging from WARNING to INFO",
    )
    parser.add_argument(
        "-f",
        "--force",
        # the following makes it a boolean flag
        action="store_true",
        default=False,
        help="Force overwrite when destination file already exists",
    )
    parser.add_argument(
        "-j",
        "--jsonl",
        # type="str",
        help="JSONL file to read from or write to",
    )
    parser.add_argument(
        "-s",
        "--server",
        # type="str",
        help=f"MQTT server name/ip to connect to ({MQTT_SERVER})",
        default=MQTT_SERVER,
    )
    parser.add_argument(
        "-p",
        "--port",
        # type="int",
        help=f"MQTT port to connect to ({MQTT_PORT})",
        default=MQTT_PORT,
    )
    parser.add_argument(
        "-t",
        "--topic",
        # type="str",
        help="MQTT topic queue to listen to (for recording), usual wildcards apply (default evcerything as '#')",
        default="#",
    )
    parser.add_argument(
        "-d",
        "--delay",
        # type="int",
        default=0,
        help="For replay, override the recorded delay between messages to use an artifical value in msecs, 0 means use record value",
    )

    args = parser.parse_args()
    logLevel = "INFO" if (args.verbose) else LOGLEVEL
    setLogLevel(logLevel)

    if args.delay and int(args.delay) < 0:
        print(f"Error:delay cannot be less than zero")
        sys.exit(1)

    if not args.jsonl or not len(args.jsonl):
        print("Error: jsonl parameter must be provided")
        sys.exit(1)

    args.cmd = args.cmd.lower()

    try:
        # print(f"Command: {args.cmd}")
        if args.cmd == "record":
            record(args.server, int(args.port), args.jsonl, args.topic, args.force)
        elif args.cmd == "replay":
            replay(args.server, args.port, args.jsonl, int(args.delay))
        else:
            print(f"Error: Unknown command {args.cmd}, use record or replay")
            sys.exit(2)
    except ConnectionRefusedError:
        print(
            f"Error: Could not connect to {args.server}:{args.port}, is the port correct?"
        )
    except Exception as e:
        # deconstruct the exception type, file and line number
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"{exc_type} File:{fname} Line:{exc_tb.tb_lineno}")
        
        if type(e).__name__ == "gaierror":
            print(
                f"Error: Could connect to {args.server}:{args.port}, are the server credentials correct?"
            )
        elif type(e).__name__ == "ValueError":
            # .:
            if str(e) == "Invalid subscription filter.":
                print(f"Error: topic ({args.topic}) wildcard is incorrect")
            else:
                print(f"Error: {type(e).__name__}")
        else:
            print(f"Error: {type(e).__name__}")

        sys.exit(2)


# ----------------------------------------------------------------------------

if __name__ == "__main__":

    main()
