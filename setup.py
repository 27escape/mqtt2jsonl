from setuptools import setup, find_packages

setup(
    name='mqtt2jsonl',
    version='0.1.0',
    author='Kevin Mulholland',
    description='Record and replay of MQTT messages to/from a JSONL file',
    packages=find_packages(),
    install_requires=[
        'paho-mqtt',
        'jsonline',
    ],
)
