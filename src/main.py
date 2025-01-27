import datetime
import streamlit as st
import pandas as pd
from kafka_handler import KafkaConfig, setup_kafka_consumer
import json
import altair as alt
import logging
import os

# Constants for date file name and kafka consumer topics
DATA_FILE_NAME = "src/data.json"
KAFKA_CONSUMER_TOPICS = os.environ.get("KAFKA_CONSUMER_TOPICS").split(", ")

# Setup Basic logging
logging.basicConfig(level=logging.INFO)

def get_kafka_consumer() -> dict:
    """Set up the Kafka consumer and return it."""
    kafka_config = KafkaConfig()
    consumer = setup_kafka_consumer(kafka_config, KAFKA_CONSUMER_TOPICS)
    return consumer


def save_data_to_json(data: dict, file_name: str) -> None:
    """Save the dashboard data to a json file. This is used to store the data between multiple streamlit sessions. 
    Otherwise with every page reload the data would be lost."""
    with open(file_name, "w") as file:
        json.dump(data, file)


def load_data_from_json(file_name: str) -> dict:
    """Load the dashboard data from a json file. If the file does not exist or is empty, return an empty dictionary."""
    try:
        with open(file_name, "r") as file:
            return json.load(file)
    except:
        return {}


def get_perceived_temperature_value_timestamp(message) -> tuple:
    """Get the perceived temperature value and timestamp as a tuple from the message."""
    # Ovveride the message with the json string from the message
    message = message["message"]

    # get the perceived temperature value and timestamp from the json object
    payload = json.loads(message)["payload"]
    value = payload["perceived_temperature"]
    timestamp = payload["timestamp"]
    
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m %H:%M:%S")

    return value, timestamp


def get_humidity_value_timestamp(message) -> tuple:
    """Get the humidity value and timestamp as a tuple from the message."""

    # get the humidity value and timestamp from the json object
    value = message["humidity"]
    timestamp = message["timestamp"]
    
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m %H:%M:%S")

    return value, timestamp


def get_temperature_value_timestamp(message) -> tuple:
    """Get the temperature value and timestamp as a tuple from the message."""

    # get the temperature value and timestamp from the json object
    value = message["temperature_c"]
    timestamp = message["timestamp"]
    
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m %H:%M:%S")

    return value, timestamp


def update_df_and_dashboard(
    data: list, dashboard, y_axis: str, x_axis: str
) -> None:
    """Create pandas data frame, an chart for the data frame and update the dashboard with the new chart."""
    data_frame = pd.DataFrame(data)
    
    # Create the chart with the data frame and set the axis labels
    chart = (
        alt.Chart(data_frame)
        .mark_line()
        .encode(
            x=alt.X("timestamp", title=x_axis),
            y=alt.Y("value", title=y_axis),
            tooltip="value",
        )
        .interactive()
    )
    
    # Update the dashboard with the new chart
    dashboard.altair_chart(chart, use_container_width=True)


def setup_streamlit_dashboard() -> dict:
    """Create the basic streamlit setup for the dashboard and return the empty dashboards."""
    
    # set the title and description of the dashboard
    st.title("Kafka Dashboard")

    # create empty dashboards for the data with titles
    st.subheader("Temperatures")
    temp_dashboard = st.empty()
    st.subheader("Humidity")
    humidity_dashboard = st.empty()
    st.subheader("Perceived Temperature")
    perceived_temp_dashboard = st.empty()

    # create map for dashboards
    return {
        "temperatures": temp_dashboard,
        "humidity": humidity_dashboard,
        "perceived_temperature": perceived_temp_dashboard,
    }


def add_data(data_dict, value_timestamp, key) -> None:
    """Add the value and timestamp to the data dictionary and save the data to the json file."""
    
    # Get the list for the topic. In the corresponding list append the dict of the value and timestamp
    data_dict[key].append(
        {"timestamp": value_timestamp[1], "value": value_timestamp[0]}
    )
    
    # Make sure the list does not get too long. 5000 is an abitrary number but during testing it was a good number for dashboard entries
    if len(data_dict[key]) > 5000:
        data_dict[key].pop(0)

    # Save the data in the json file
    save_data_to_json(data_dict, DATA_FILE_NAME)


def main() -> None:
    # Get the kafka consumer for the different topics
    kafka_consumer = get_kafka_consumer()

    # If exists: load the old data from the json file
    # Data is basically a dictionary with the topics as keys and lists of dictionaries as values. Each dictionary in the list contains the value and timestamp of the message.
    data = load_data_from_json(DATA_FILE_NAME)

    # if there is not data already create an empty dictionary
    if not data:
        data = {
            "temperatures": [],
            "humidity": [],
            "perceived_temperature": [],
        }

    # Create the streamlit app and get the empty dashboards
    dashboards = setup_streamlit_dashboard()
    
    # Check the topic for every message and append the data to the corresponding list
    # Always: 1) get the value and timestamp tuple from the message. 2) add the data to the data dictionary. 3) update the dashboard with the new data
    for message in kafka_consumer:
        match message.topic:
            case "iot.devices.humidity":
                value_timestamp: tuple = get_humidity_value_timestamp(message.value)
                add_data(data, value_timestamp, key="humidity")
                update_df_and_dashboard(
                    data["humidity"],
                    dashboards["humidity"],
                    y_axis="Luftfeuchtigkeit/%",
                    x_axis="Uhrzeit",
                )
                pass

            case "iot.devices.temperatures":
                value_timestamp: tuple = get_temperature_value_timestamp(message.value)
                add_data(data, value_timestamp, key="temperatures")
                update_df_and_dashboard(
                    data["temperatures"],
                    dashboards["temperatures"],
                    y_axis="Temperatur/°C",
                    x_axis="Uhrzeit",
                )
                pass

            case "iot.services.perceived_temperatures":
                value_timestamp: tuple = get_perceived_temperature_value_timestamp(
                    message.value
                )
                add_data(data, value_timestamp, key="perceived_temperature")
                update_df_and_dashboard(
                    data["perceived_temperature"],
                    dashboards["perceived_temperature"],
                    y_axis="gefühlte Temperatur/°C",
                    x_axis="Uhrzeit",
                )
                pass


if __name__ == "__main__":
    main()
