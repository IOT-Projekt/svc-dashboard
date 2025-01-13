import datetime
import streamlit as st
import pandas as pd
from kafka_handler import KafkaConfig, setup_kafka_consumer
import json
import altair as alt

def get_kafka_consumer() -> dict:
    kafka_config = KafkaConfig()
    consumer = setup_kafka_consumer(
        kafka_config, ["temperatures", "humidity", "perceived_temperature"]
    )
    return consumer


def get_perceived_temperature_value_timestamp(message) -> tuple:
    # get the json string from the message
    message = message["message"]

    # get the perceived temperature value and timestamp from the json object
    payload = json.loads(message)["payload"]
    value = payload["perceived_temperature"]
    timestamp = payload["timestamp"]
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

    return value, timestamp


def get_humidity_value_timestamp(message) -> tuple:
    # get the json string from the message
    message = message["message"]

    # get the humidity value and timestamp from the json object
    value = json.loads(message)["humidity"]
    timestamp = json.loads(message)["timestamp"]
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
    
    return value, timestamp


def get_temperature_value_timestamp(message) -> tuple:
    # get the json string from the message
    message = message["message"]

    # get the temperature value and timestamp from the json object
    value = json.loads(message)["temperature_c"]
    timestamp = json.loads(message)["timestamp"]
    # convert the timestamp to a datetime object
    timestamp = datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")

    return value, timestamp


def update_df_and_dashboard(
    data: list, data_frame: pd.DataFrame, dashboard, y_axis: str, x_axis: str
) -> None:
    data_frame = pd.DataFrame(data)
    chart = alt.Chart(data_frame).mark_line().encode(
        x=alt.X('timestamp', title=x_axis),
        y=alt.Y('value', title=y_axis),
        tooltip='value'
    ).interactive()
    dashboard.altair_chart(chart, use_container_width=True)


def setup_streamlit_dashboard() -> dict:
    # set the title and description of the dashboard
    st.title("Kafka Dashboard")

    # create empty charts for the data with titles
    st.subheader("Temperatures")
    temp_chart = st.empty()
    st.subheader("Humidity")
    humidity_chart = st.empty()
    st.subheader("Perceived Temperature")
    perceived_temp_chart = st.empty()

    # create map for dashboards
    return {
        "temperatures": temp_chart,
        "humidity": humidity_chart,
        "perceived_temperature": perceived_temp_chart,
    }


def add_data(list, value_timestamp):
    list.append({"timestamp": value_timestamp[1], "value": value_timestamp[0]})
    if len(list) > 15000:
        list.pop(0)


def main() -> None:
    kafka_consumer = get_kafka_consumer()

    # Mapping for value lists
    data = {
        "temperatures": [],
        "humidity": [],
        "perceived_temperature": [],
    }

    # Mapping for data frames
    data_frames = {
        "temperatures": pd.DataFrame(),
        "humidity": pd.DataFrame(),
        "perceived_temperature": pd.DataFrame(),
    }

    # Create the streamlit app
    dashboards = setup_streamlit_dashboard()

    # Check the topic for every message and append it to the corresponding list
    for message in kafka_consumer:
        match message.topic:
            # Check the topic and append the value and timestamp to the corresponding list
            case "humidity":
                value_timestamp: tuple = get_humidity_value_timestamp(message.value)
                add_data(data["humidity"], value_timestamp)
                update_df_and_dashboard(
                    data["humidity"],
                    data_frames["humidity"],
                    dashboards["humidity"],
                    y_axis="Luftfeuchtigkeit/%",
                    x_axis="Uhrzeit",
                )
                pass

            case "temperatures":
                value_timestamp: tuple = get_temperature_value_timestamp(message.value)
                add_data(data["temperatures"], value_timestamp)
                update_df_and_dashboard(
                    data["temperatures"],
                    data_frames["temperatures"],
                    dashboards["temperatures"],
                    y_axis="Temperatur/°C",
                    x_axis="Uhrzeit",
                )
                pass

            case "perceived_temperature":
                value_timestamp: tuple = get_perceived_temperature_value_timestamp(
                    message.value
                )
                add_data(data["perceived_temperature"], value_timestamp)
                update_df_and_dashboard(
                    data["perceived_temperature"],
                    data_frames["perceived_temperature"],
                    dashboards["perceived_temperature"],
                    y_axis="gefühlte Temperatur/°C",
                    x_axis="Uhrzeit",
                )
                pass


if __name__ == "__main__":
    main()
