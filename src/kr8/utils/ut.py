import platform
import socket
import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Slack configuration
SLACK_TOKEN = "xoxb-1268836013186-7230300082160-syjqHaSER9KmsYGlAFatkmEj"  # Make sure this is your actual token
SLACK_CHANNEL = "rozy-usage"  # Ensure this is the correct Slack channel

# Initialize events list (if it's not already in session state)
if "events" not in st.session_state:
    st.session_state["events"] = []

# Global variables to store events, sent events, and scheduler
events = st.session_state["events"]
sent_events = []
scheduler = None

def get_host_info():
    host_info = {
        "hostname": socket.gethostname(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "system": platform.system()        
    }
    return host_info

def log_event(event_type, details, response=None):
    event = {"type": event_type, "details": details}
    if response:
        first_line = response[:75]  # Capture the first 50 characters of the response
        response_length = len(response)
        event["response"] = {
            "first_line": first_line,
            "length": response_length
        }
    print(f"Logging event: {event}")  # Debug print
    events.append(event)
    st.session_state["events"] = events

def send_to_slack(message):
    client = WebClient(token=SLACK_TOKEN)
    try:
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=message
        )
        print(f"Message sent to Slack: {message}")  # Debug print
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")

def send_usage_data():
    global sent_events
    new_events = [event for event in events if event not in sent_events]
    
    if not new_events:
        print("No new events to send.")
        return
    
    host_info = get_host_info()
    formatted_host_info = (
        f"*host_info:*\n"
        f"\t*hostname:* {host_info['hostname']}\n"
        f"\t*ip_address:* {host_info['ip_address']}\n"
        f"\t*system:* {host_info['system']}\n"
    )
    
    formatted_events = "*Events:*\n"
    for event in new_events:
        response_details = event.get('response', {})
        response_first_line = response_details.get('first_line', '')
        response_length = response_details.get('length', '')
        formatted_events += (f"""\t*Event Type:* {event['type']},
            *Event Details:* {event['details']}\n
            *Response First Line:* {response_first_line}\n
            *Length:* {response_length}\n
            =============================\n"""
        )
    
    message = f"{formatted_host_info}{formatted_events}"
    print(f"Sending usage data: {message}")  # Debug print
    send_to_slack(message)
    
    # Update sent_events with the new events
    sent_events.extend(new_events)

def initialize_usage_tracking():
    global scheduler

    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(send_usage_data, 'interval', minutes=1)  # Adjust the interval as needed
        scheduler.start()
        print("Scheduler started")  # Debug print

        atexit.register(lambda: scheduler.shutdown())

initialize_usage_tracking()