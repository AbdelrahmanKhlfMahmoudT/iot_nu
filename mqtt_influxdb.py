"""
mqtt_influxdb.py

Handles MQTT communication with HiveMQ Cloud and stores
sensor measurements in InfluxDB Cloud.

Responsibilities:
    - Receive sensor measurements from the sensor process.
    - Publish sensor data to HiveMQ Cloud.
    - Store sensor data in InfluxDB Cloud.
    - Subscribe to the LED control topic.
    - Forward LED commands to the LED process.
"""

import os
import ssl

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


# ---------------------------------------------------------------------------
# MQTT + InfluxDB Process
# ---------------------------------------------------------------------------

def mqtt_process(distance_queue, led_queue):

    # -----------------------------------------------------------------------
    # MQTT Configuration
    # -----------------------------------------------------------------------

    mqtt_host = os.getenv("MQTT_HOST")
    mqtt_port = int(os.getenv("MQTT_PORT", "8883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")

    if not all([mqtt_host, mqtt_username, mqtt_password]):
        raise RuntimeError(
            "MQTT configuration environment variables are not set."
        )

    # -----------------------------------------------------------------------
    # InfluxDB Configuration
    # -----------------------------------------------------------------------

    influx_url = os.getenv("INFLUX_URL")
    influx_token = os.getenv("INFLUX_TOKEN")
    influx_org = os.getenv("INFLUX_ORG")
    influx_bucket = os.getenv("INFLUX_BUCKET")

    if not all([
        influx_url,
        influx_token,
        influx_org,
        influx_bucket
    ]):
        raise RuntimeError(
            "InfluxDB configuration environment variables are not set."
        )

    # -----------------------------------------------------------------------
    # MQTT Topics
    # -----------------------------------------------------------------------

    DISTANCE_TOPIC = "sensor/distance"
    LED_TOPIC = "led/control"

    # -----------------------------------------------------------------------
    # InfluxDB Client
    # -----------------------------------------------------------------------

    influx_client = InfluxDBClient(
        url=influx_url,
        token=influx_token,
        org=influx_org
    )

    write_api = influx_client.write_api(
        write_options=SYNCHRONOUS
    )

    # -----------------------------------------------------------------------
    # MQTT Callbacks
    # -----------------------------------------------------------------------

    def on_connect(client, userdata, flags, rc):

        if rc == 0:
            print("Connected to HiveMQ Cloud.")

            result = client.subscribe(LED_TOPIC)

            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                print(f"Subscribed to: {LED_TOPIC}")
            else:
                print("Failed to subscribe to LED topic.")

        else:
            print(f"MQTT connection failed. Error code: {rc}")

    def on_message(client, userdata, msg):

        value = msg.payload.decode()

        print(f"[MQTT] {msg.topic} -> {value}")

        if msg.topic == LED_TOPIC:
            led_queue.put(value)

    # -----------------------------------------------------------------------
    # MQTT Client
    # -----------------------------------------------------------------------

    client = mqtt.Client()

    client.username_pw_set(
        username=mqtt_username,
        password=mqtt_password
    )

    # Enable TLS encryption
    client.tls_set(
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )

    client.on_connect = on_connect
    client.on_message = on_message

    # -----------------------------------------------------------------------
    # Connect to HiveMQ Cloud
    # -----------------------------------------------------------------------

    print("Connecting to HiveMQ Cloud...")

    client.connect(
        mqtt_host,
        mqtt_port,
        60
    )

    # Start MQTT network loop
    client.loop_start()

    print("MQTT + InfluxDB process started.")

    try:

        while True:

            # ---------------------------------------------------------------
            # Receive distance from sensor process
            # ---------------------------------------------------------------

            distance = distance_queue.get()

            print(
                f"[Sensor] Distance: "
                f"{distance:.2f} cm"
            )

            # ---------------------------------------------------------------
            # Publish distance through MQTT
            # ---------------------------------------------------------------

            result = client.publish(
                DISTANCE_TOPIC,
                distance
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(
                    f"[MQTT] Published: "
                    f"{distance:.2f} cm"
                )
            else:
                print(
                    f"[MQTT] Publish failed. "
                    f"Error code: {result.rc}"
                )

            # ---------------------------------------------------------------
            # Store distance in InfluxDB
            # ---------------------------------------------------------------

            point = (
                Point("distance")
                .field("value", float(distance))
            )

            write_api.write(
                bucket=influx_bucket,
                org=influx_org,
                record=point
            )

            print("[InfluxDB] Data stored successfully.")

    except KeyboardInterrupt:

        print("\nMQTT + InfluxDB process stopped.")

    finally:

        # Stop MQTT communication
        client.loop_stop()
        client.disconnect()

        # Close InfluxDB connection
        influx_client.close()

        print("Connections closed.")


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
#
# This function is designed to be called by the main multiprocessing
# application, where distance_queue and led_queue are multiprocessing.Queue
# objects.
#
# Example:
#
# mqtt_process(distance_queue, led_queue)
#
# ---------------------------------------------------------------------------
