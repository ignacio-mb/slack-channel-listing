import os
import csv
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Your Slack API token
slack_token = 'your-slack-api-token' 

# Create a Slack client
client = WebClient(token=slack_token)

# Function to get all channels in the workspace
def get_all_channels():
    logging.debug("Fetching all channels...")
    channels = []
    next_cursor = None

    try:
        while True:
            response = client.conversations_list(limit=1000, types='public_channel,private_channel', cursor=next_cursor)
            channels.extend(response.get('channels', []))
            next_cursor = response['response_metadata'].get('next_cursor', '')
            
            logging.debug(f"Fetched {len(response.get('channels', []))} channels. Total so far: {len(channels)}")
            
            if not next_cursor:  # No more channels to fetch
                break
    except SlackApiError as e:
        logging.error(f"Error fetching channels: {e.response['error']}")

    return channels

# Function to get user emails in a channel
def get_channel_users(channel_id):
    logging.debug(f"Fetching users for channel ID: {channel_id}")
    user_emails = []
    try:
        response = client.conversations_members(channel=channel_id)
        user_ids = response.get('members', [])
        
        # Fetch email addresses of the users
        for user_id in user_ids:
            user_info = client.users_info(user=user_id)
            email = user_info['user']['profile'].get('email', '')
            if email:
                user_emails.append(email)
    except SlackApiError as e:
        logging.error(f"Error fetching members for channel {channel_id}: {e.response['error']}")
    logging.debug(f"Fetched {len(user_emails)} emails for channel ID: {channel_id}")
    return user_emails

# Function to get information about integrations in a channel
def get_channel_integrations(channel_id):
    logging.debug(f"Fetching integrations for channel ID: {channel_id}")
    try:
        response = client.conversations_info(channel=channel_id)
        channel_info = response.get('channel', {})
        connected_apps = channel_info.get('connected_team_ids', [])
        logging.debug(f"Fetched integrations for channel ID: {channel_id}: {connected_apps}")
        return connected_apps
    except SlackApiError as e:
        logging.error(f"Error fetching integrations for channel {channel_id}: {e.response['error']}")
        return []

# Get the next available filename
def get_next_filename(base_name):
    index = 1
    while os.path.exists(f"{base_name}{index}.csv"):
        index += 1
    return f"{base_name}{index}.csv"

# Main script
def main():
    logging.debug("Starting script...")
    channels = get_all_channels()

    if not channels:
        logging.error("No channels were fetched. Exiting script.")
        return

    # Prepare CSV file
    file_name = get_next_filename("channels_list")
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Channel Name", "Channel ID", "List of Users (Emails)", "is_external", "Integrations/Apps"])

        for channel in channels:
            channel_name = channel.get('name')
            channel_id = channel.get('id')
            channel_type = channel.get('is_shared', False)
            logging.debug(f"Channel: {channel_name}, Type: {'shared' if channel_type else 'internal'}")
            
            user_emails = get_channel_users(channel_id)
            integrations = get_channel_integrations(channel_id)
            
            if not channel_name or not channel_id:
                logging.warning(f"Channel data incomplete for: {channel}. Skipping.")
                continue
            
            # Determine if the channel is external
            is_external = channel_name.startswith('ext') and any('@metabase.com' not in email for email in user_emails)
            
            writer.writerow([channel_name, channel_id, ", ".join(user_emails), is_external, ", ".join(integrations)])

            # Log the channel's data
            logging.info(f"Channel: {channel_name}, ID: {channel_id}, Users: {len(user_emails)}, External: {is_external}, Integrations: {integrations}")

    logging.info(f"Data written to {file_name}")

if __name__ == "__main__":
    main()
