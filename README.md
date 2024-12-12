# Meshtastic to Jira Integration

This repository provides an integration that listens for messages from a Meshtastic network, forwards them to a specified MQTT broker, and then creates or updates Jira issues with those messages as comments. It also re-publishes these messages to a dedicated `jira` MQTT topic.

## Features

1. **Meshtastic Integration:**  
   Connects to a Meshtastic device over a serial interface and listens for incoming messages.
   
2. **MQTT Forwarding:**  
   Incoming messages from Meshtastic are published to an MQTT topic (e.g., `msh`), and Jira-related updates are published to a separate MQTT topic (e.g., `jira`).

3. **Jira Issue Management:**  
   Uses the Jira API (Cloud) to:
   - Create a new Jira issue for each new device ID encountered.
   - Append subsequent messages from that device as comments to the created Jira issue.

## Prerequisites

- **Meshtastic device and Meshtastic Python library**  
  Ensure you have a connected Meshtastic device (e.g., a T-Beam) and the `meshtastic` Python library installed.
  
- **MQTT Broker**  
  You’ll need an accessible MQTT broker (like Mosquitto) running and configured.
  
- **Jira Cloud Account & API Token**  
  Create a Jira API token and have your Jira Cloud site URL, project key, and other details ready.

- **Python 3.8+ and Dependencies**  
  Make sure Python 3.8 or later is installed.  
  Install required packages:
  ```bash
  pip install meshtastic paho-mqtt jira configparser
  ```

## Configuration

1. **`config/config.properties`**  
   Place a configuration file at `config/config.properties` with the following keys:

   ```properties
   [mqtt]
   broker=127.0.0.1
   port=1883
   topic_in=msh
   topic_jira=jira

   [jira]
   server=https://yourjira.atlassian.net
   project=YOURPROJECTKEY
   issue_type=Task
   # For Jira Cloud, use basic_auth with email and api_token:
   username=your_email@domain.com
   api_token=your_jira_api_token
   ```

   Adjust the values according to your environment.

2. **Serial Interface**  
   Update the `SerialInterface` line in the code to match your device’s port, e.g.:
   ```python
   interface = meshtastic.serial_interface.SerialInterface("/dev/cu.usbserial-0001")
   ```
   On Linux, this might look like `/dev/ttyUSB0`, or another appropriate device file.

## Running the Application

1. **Start Your MQTT Broker**  
   Ensure your MQTT broker is running and reachable.

2. **Run the Script**  
   ```bash
   python your_script.py
   ```

   The script will:
   - Connect to the Meshtastic device.
   - Start listening for incoming messages.
   - Publish them to the MQTT topic defined in `config.properties`.
   - Create or update Jira issues for each unique device ID.
   - Forward messages as comments to the respective Jira issue.
   - Publish messages to the `jira` MQTT topic for downstream integrations.

3. **Sending Test Messages**  
   The script’s console interface allows you to send test messages. Type a message and press Enter to simulate sending from a device. Type `exit` to stop sending test messages.

## Troubleshooting

- **Jira Auth Errors:**  
  If you see errors related to auth tokens, verify you’re using `basic_auth=('your_email@domain.com', 'your_api_token')` when creating the `JIRA` client.
  
- **MQTT Connectivity Issues:**  
  Check that the MQTT broker is running and that the correct host and port are set in `config.properties`.

- **Meshtastic Connection Errors:**  
  Verify that the device is powered, the serial port is correct, and the `meshtastic` library is installed.

## License

This project is provided as-is under an open source license. Check the `LICENSE` file for details.
