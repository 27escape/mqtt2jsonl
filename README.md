#  mqtt2jsonl

This is a simple script to listen to MQTT messages and store them into a [JSONL](https://jsonlines.org/) file. This JSONL file can then be replayed at a later date, which is useful for testing MQTT systems.

I had a quick look on the Internet and could not see anything similar, though it likely exists, this just helps me at the moment.

## Installation

**TODO: Fix this when I understand how to package things properly**

This is a python3 script, if that does not match your requirements, please look elsewhere.

This is my first python code, so I have not created an account with PyPI or whatever, so you need to build and install from this dist

build it
```
python3 setup.py sdist
```

install it
```
pip install dist/mqtt2jsonl-0.1.0.tar.gz
```

If you want to make changes and rebuild, remember to update the version number in the `setup.py` file.

## Using it

Assumption that you are using linux/unix otherwise prefix the command with `python3`, assuming your other OS has python3 installed and its accessible from a command prompt.

Help is available
```
./mqtt2jsonl -h
usage: mqtt2jsonl [-h] [-v] [-f] [-j JSONL] [-s SERVER] [-p PORT] [-t TOPIC] [-d DELAY] cmd

Either record or replay MQTT via a JSONL file

positional arguments:
  cmd                   Command to perform against the MQTT topic queue, 'record' or 'replay'

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase level of logging from WARNING to INFO
  -f, --force           Force overwrite when destination file already exists
  -j JSONL, --jsonl JSONL
                        JSONL file to read from or write to
  -s SERVER, --server SERVER
                        MQTT server name/ip to connect to (localhost)
  -p PORT, --port PORT  MQTT port to connect to (1883)
  -t TOPIC, --topic TOPIC
                        MQTT topic queue to listen to (for recording), usual wildcards apply (default everying as '#')
  -d DELAY, --delay DELAY
                        For replay, override the recorded delay between messages to use an artifical
                        value in msecs, 0 means use record value
```

### Record

Connect to default localhost port 1883, with a wildcard topic, overwriting any previous file
```
./mqtt2jsonl -j /tmp/record.jsonl record -t '/photos/#' -f
```

Connect to to named server and port, use default topic of everything (#) 
```
./mqtt2jsonl -j /tmp/record.jsonl record --server some_mqtt_server --port 1000 
```


### Replay

Connect to default localhost port 1883, replay at the recorded rate
```
./mqtt2jsonl -j /tmp/record.jsonl replay 
```

Connect to to named server and port, replay at a fast rate of one message per 5ms 
```
./mqtt2jsonl -j /tmp/record.jsonl record --server some_mqtt_server --port 1000  --delay=5
```


## Improvements / TODO

There are a few things that could possibly make this a better more general tool but I don't need these features right now

- [ ] Create a PyPI account and upload it there
- [ ] Log in with a username/password
- [ ] Log into a MQTT server that uses TLS
