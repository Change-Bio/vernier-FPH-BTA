# -*- coding: utf-8 -*-
from time import sleep
import click
from pioreactor.whoami import get_unit_name, get_assigned_experiment_name
from pioreactor.background_jobs.base import BackgroundJob
import serial
import json
from pioreactor.utils.timing import RepeatedTimer
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import produce_metadata
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import register_source_to_sink
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import TopicToParserToTable
from pioreactor.utils import timing
from pioreactor.pubsub import QOS
from pioreactor.types import MQTTMessage
from pioreactor.config import config
from pioreactor.plugin_management import get_plugins
from pioreactor.calibrations import load_active_calibration

__plugin_summary__ = "Reads pH from Vernier FPH-BTA probe"
__plugin_version__ = "0.0.2"
__plugin_name__ = "Vernier FPH-BTA"
__plugin_author__ = "Noah Sprent"
__plugin_homepage__ = "https://github.com/noahsprent/vernier-FPH-BTA"


def __dir__():
    return ['click_read_ph']


def parser(topic, payload) -> dict:
    metadata = produce_metadata(topic)
    return {
        "experiment": metadata.experiment,
        "pioreactor_unit": metadata.pioreactor_unit,
        "timestamp": timing.current_utc_timestamp(),
        "ph_reading": float(payload),
    }


register_source_to_sink(
    TopicToParserToTable(
        ["pioreactor/+/+/vernier_fph_bta/ph_reading"],
        parser,
        "ph_readings",
    )
)

class ReadPh(BackgroundJob):

    job_name="vernier_fph_bta"
    published_settings = {
        "ph_reading": {"datatype": "float", "settable": False},
        "pin": {"datatype": "string", "settable": True},
        "slope": {"datatype": "float", "settable": False},
        "intercept": {"datatype": "float", "settable": False},
    }

    def __init__(self, unit, experiment, **kwargs):
        super().__init__(unit=unit, experiment=experiment)

        ph_calibration = get_plugins()["ph_calibration"].module.PHCalibration # we need to create this subclass here in order for load_active_calibration to work
        self.ph_cal = load_active_calibration("ph_probe")

        self.pin = config.get("fph_bta.config", "pin")
        
        self.start_reading_ph()     

    def on_ready(self):
        self.logger.debug(f"Reading pH from {self.pin} from MQTT...")

    def on_disconnected(self):
        self.logger.debug(f"No longer reading pH from MQTT")

    def start_reading_ph(self) -> None:
        self.subscribe_and_callback(
            callback = self.read_ph,
            subscriptions = f"pioreactor/{self.unit}/+/pioreactor_read_serial/{self.pin}",
            qos=QOS.AT_LEAST_ONCE,
        )

    def read_ph(self, reading_message: MQTTMessage) -> None:
        value = reading_message.payload
        float_value = float(value.decode('utf-8'))
        self.ph_reading = self.ph_cal.y_to_x(float_value) 
        return self.ph_reading

@click.command(name="vernier_fph_bta", help=__plugin_summary__)
def click_read_ph():

    unit = get_unit_name()
    experiment = get_assigned_experiment_name(unit)
    job = ReadPh(
        unit=unit,
        experiment=experiment,
        )
    job.block_until_disconnected()
