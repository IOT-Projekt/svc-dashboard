import streamlit as st
import pandas as pd
import threading
import time
from kafka_handler import KafkaConfig, setup_kafka_consumer
import json

def get_kafka_consumer() -> dict:
    kafka_config = KafkaConfig()
    consumers = {
        "temperatures": setup_kafka_consumer(kafka_config, ["temperatures"]),
        "humidity": setup_kafka_consumer(kafka_config, ["humidity"]),
        "perceived_temperature": setup_kafka_consumer(kafka_config, ["perceived_temperature"]),
    }
    return consumers

def read_messages(consumer, key, data, lock):
    while True:
        for message in consumer:
            value_timestamp: tuple = get_value_timestamp(message)
            print(value_timestamp[0], value_timestamp[1])
            with lock:
                data[key].append({"timestamp": value_timestamp[1], "value": value_timestamp[0]})
                if len(data[key]) > 10000:
                    data[key].pop(0)
        time.sleep(1)

def get_value_timestamp(message) -> tuple:
    message = message.value["message"]
    print(message)
    if "payload" in message:
        payload = json.loads(message)["payload"]
        value = payload["perceived_temperature"] 
        timestamp = payload["timestamp"]
    else:
        value = json.loads(message)["humidity"] if "humidity" in message else json.loads(message)["temperature_c"] 
        timestamp = json.loads(message)["timestamp"]
    return value, timestamp

def main() -> None:
    consumers = get_kafka_consumer()
    data = {
        "temperatures": [],
        "humidity": [],
        "perceived_temperature": [],
    }
    lock = threading.Lock()

    for key, consumer in consumers.items():
        threading.Thread(target=read_messages, args=(consumer, key, data, lock), daemon=True).start()

    st.title("Kafka Streamlit Dashboard")
    st.write("Real-time data from Kafka consumers")

    temp_chart_placeholder = st.empty()
    humidity_chart_placeholder = st.empty()
    perceived_temp_chart_placeholder = st.empty()

    while True:
        with lock:
            temp_df = pd.DataFrame(data["temperatures"])
            humidity_df = pd.DataFrame(data["humidity"])
            perceived_temp_df = pd.DataFrame(data["perceived_temperature"])

        if not temp_df.empty:
            temp_chart_placeholder.line_chart(temp_df.set_index("timestamp"))
        if not humidity_df.empty:
            humidity_chart_placeholder.line_chart(humidity_df.set_index("timestamp"))
        if not perceived_temp_df.empty:
            perceived_temp_chart_placeholder.line_chart(perceived_temp_df.set_index("timestamp"))

        time.sleep(1)

if __name__ == "__main__":
    main()