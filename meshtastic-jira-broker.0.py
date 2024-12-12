import meshtastic.serial_interface
import paho.mqtt.client as mqtt
import threading
import time
import traceback
import configparser
from jira import JIRA

# Load configuration from config file
config = configparser.ConfigParser()
config.read('config/config.properties')

# JIRA Configuration
JIRA_SERVER = config.get('jira', 'server', fallback='https://yourjira.atlassian.net')
JIRA_TOKEN = config.get('jira', 'api_token', fallback='your_api_token')
JIRA_PROJECT = config.get('jira', 'project', fallback='MESH')
JIRA_ISSUE_TYPE = config.get('jira', 'issue_type', fallback='Task')

# MQTT setup
MQTT_BROKER = config.get('mqtt', 'broker', fallback='127.0.0.1')
MQTT_PORT = config.getint('mqtt', 'port', fallback=1883)
MQTT_TOPIC = config.get('mqtt', 'topic_in', fallback='msh')  # incoming messages from Meshtastic
MQTT_JIRA_TOPIC = config.get('mqtt', 'topic_jira', fallback='jira')  # forwarded messages for Jira

mqtt_client = mqtt.Client()

# Dictionary to track which device_id maps to which JIRA issue key
device_issue_map = {}

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print("DEBUG: Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"ERROR: Failed to connect to MQTT broker, return code {rc}")

def on_mqtt_message(client, userdata, msg):
    try:
        message = msg.payload.decode("utf-8", errors="replace")
        print(f"DEBUG: MQTT message received on '{msg.topic}': {message}")
        # No direct processing here since these are incoming from Meshtastic. 
        # The main handling is done in on_receive and post_to_jira.
    except Exception as e:
        print(f"ERROR: Exception in MQTT message callback: {e}")
        traceback.print_exc()

mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()  # Ensure MQTT loop is running

# Initialize JIRA client using token
try:

    from jira import JIRA

    jira_client = JIRA(server='https://you.atlassian.net', basic_auth=('you@gmail.com', 'YOUR ATLASSIAN API TOKEN')
)

   #jira_client = JIRA(server=JIRA_SERVER, token_auth=JIRA_TOKEN)
    print("DEBUG: Connected to JIRA successfully with API token")
except Exception as e:
    print(f"ERROR: Failed to connect to JIRA: {e}")
    traceback.print_exc()
    jira_client = None

# Meshtastic interface - update with correct serial port
# This works on macOS with a single node connection to serial.
# Change for Linux, Windows to suit your port arrangement.
interface = meshtastic.serial_interface.SerialInterface("/dev/cu.usbserial-0001")

def on_receive(interface, packet):
    print(f"DEBUG: Received packet: {packet}")
    try:
        if "decoded" in packet and "payload" in packet["decoded"]:
            payload = packet["decoded"]["payload"]

            # Attempt to decode the payload
            if isinstance(payload, bytes):
                try:
                    message = payload.decode("utf-8")
                except UnicodeDecodeError:
                    message = str(payload)
            else:
                message = str(payload)

            # Extract device_id from packet if available
            # Meshtastic packets often contain 'fromId' representing the sender node.
            device_id = packet.get("fromId")
            if device_id is None:
                # Fallback if no fromId is available, use from (nodeNum) or a generic placeholder
                device_id = packet.get("from", "unknown_device")

            print(f"DEBUG: Decoded message from device '{device_id}': {message}")

            # Publish the incoming Meshtastic message to MQTT topic_in
            mqtt_client.publish(MQTT_TOPIC, message)
            print(f"DEBUG: Published to MQTT topic '{MQTT_TOPIC}': {message}")

            # Forward to channel
            forward_to_chn(message)

            # Post to JIRA (create or update issue)
            post_to_jira(device_id, message)
            
            # Also forward to the jira MQTT topic
            mqtt_client.publish(MQTT_JIRA_TOPIC, message)
            print(f"DEBUG: Published to JIRA MQTT topic '{MQTT_JIRA_TOPIC}': {message}")
        else:
            print("DEBUG: Packet does not contain a decoded payload.")
    except Exception as e:
        print(f"ERROR: Exception while processing packet: {e}")
        traceback.print_exc()

def forward_to_chn(message):
    try:
        print(f"DEBUG: Forwarding message to channel: {message}")
        interface.sendText(message, wantAck=True, channelIndex=0)
        print("DEBUG: Message forwarded to channel.")
    except Exception as e:
        print(f"ERROR: Exception while sending message to channel: {e}")
        traceback.print_exc()

def post_to_jira(device_id, message):
    if jira_client is None:
        print("ERROR: JIRA client not initialized, cannot post to JIRA.")
        return

    try:
        # Check if we already have an issue for this device
        if device_id not in device_issue_map:
            # Create a new JIRA issue for this device
            issue_dict = {
                'project': {'key': JIRA_PROJECT},
                'summary': f"Device {device_id} Issue",
                'description': f"Issue collecting messages from device {device_id}.",
                'issuetype': {'name': JIRA_ISSUE_TYPE}
            }
            new_issue = jira_client.create_issue(fields=issue_dict)
            device_issue_map[device_id] = new_issue.key
            print(f"DEBUG: Created new JIRA issue {new_issue.key} for device {device_id}")

        # Add the message as a comment to the device's JIRA issue
        issue_key = device_issue_map[device_id]
        jira_client.add_comment(issue_key, message)
        print(f"DEBUG: Added comment to JIRA issue {issue_key}: {message}")

    except Exception as e:
        print(f"ERROR: Exception while posting to JIRA: {e}")
        traceback.print_exc()

# Function to allow test messages
def send_test_messages():
    while True:
        user_input = input("Enter a message to send (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            print("Exiting test message sender.")
            break
        try:
            print(f"DEBUG: Sending test message to Channel 0 and MQTT topic: {user_input}")
            # Send to Meshtastic default channel (0)
            interface.sendText(user_input, wantAck=True, channelIndex=0)  
            
            # Forward to channel (channel 0)
            forward_to_chn(user_input)
            
            # Simulate a device ID for testing when posting to Jira
            test_device_id = "test_device_123"
            post_to_jira(test_device_id, user_input)

            # Forward to JIRA MQTT topic as well
            mqtt_client.publish(MQTT_JIRA_TOPIC, user_input)
            print(f"DEBUG: Published test message to JIRA MQTT topic '{MQTT_JIRA_TOPIC}': {user_input}")
        except Exception as e:
            print(f"ERROR: Exception while sending test message: {e}")
            traceback.print_exc()

def listen():
    print("Listening for Meshtastic messages...")
    interface.onReceive = on_receive
    while True:
        time.sleep(0.1)

# Run the listening loop in a separate thread
listen_thread = threading.Thread(target=listen, daemon=True)
listen_thread.start()

# Allow test messages in the main thread
send_test_messages()
