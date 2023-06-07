import requests
import json
import os
import time
import base64
from datetime import datetime, timedelta

api_base_url = 'https://api.zoom.us/v2'

def get_token(zoom_account_id, zoom_client_id, zoom_client_secret):
    zoom_oauth_endpoint = 'https://zoom.us/oauth/token'
    data = {
        'grant_type': 'account_credentials',
        'account_id': zoom_account_id
    }
    auth_header = base64.b64encode(f'{zoom_client_id}:{zoom_client_secret}'.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth_header}'
    }

    try:
        response = requests.post(zoom_oauth_endpoint, data=data, headers=headers)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if e.response is not None:
            print(e.response.json())
        return None

def get_users(headers):
    url = api_base_url + '/users'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        users = response.json()
        return users['users']
    else:
        print(f"Error getting users: {response.status_code}")
        return []

def get_recordings(user_id, headers, from_date, to_date):
    url = api_base_url + f'/users/{user_id}/recordings'
    params = {
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d')
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        recordings = response.json()
        return recordings['meetings']
    else:
        print(f"Error getting recordings for user {user_id}: {response.status_code}")
        return []

def download_file(url, filepath, headers, filename, start_time):
    # Create a folder for each user inside the recording downloads folder
    folder_path = os.path.join(filepath, start_time)
    os.makedirs(folder_path, exist_ok=True)

    # Update the filepath to include the filename and start_time folders
    filepath = os.path.join(folder_path, filename)

    response = requests.get(url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    else:
        print(f"Error downloading file: {response.status_code}")
        return False


def main():
    zoom_account_id = 'ACCOUNT_ID'
    zoom_client_id = 'CLIENT_ID'
    zoom_client_secret = 'CLIENT_SECRET'
    
    access_token = get_token(zoom_account_id, zoom_client_id, zoom_client_secret)
    
    if access_token is None:
        print("Failed to get access token")
        return

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    users = get_users(headers)

    for user in users:
        user_id = user['id']
        user_email = user['email']
        print(f"Processing user {user_email}...")

        # Set the initial dates
        from_date = datetime.utcnow() - timedelta(days=365)  # One year ago
        to_date = from_date + timedelta(days=30)  # One month after from_date

        reached_current_date = False
        while not reached_current_date:
            recordings = get_recordings(user_id, headers, from_date, to_date)

            if not recordings:
                from_date = to_date
                to_date = to_date + timedelta(days=30)
                if to_date > datetime.utcnow():
                    to_date = datetime.utcnow()
                
                #time.sleep(1)
            else:

                for recording in recordings:
                    # ... (downloading and processing recordings)
                    start_time = recording['start_time']
                    
                    for file in recording['recording_files']:
                        file_url = file['download_url']
                        file_type = file['file_type']
                        file_extension = file_type.lower()
                        filename = f"{user_email}-{start_time}.{file_extension}"
                        filepath = os.path.join('downloads', user_email)

                        if not os.path.exists('downloads'):
                            os.makedirs('downloads')

                        if download_file(file_url, filepath, headers, filename, start_time):
                            print(f"\tDownloaded {filename}")
                        else:
                            print(f"\tFailed to download {filename}")

            from_date = to_date
            to_date = to_date + timedelta(days=30)
            if to_date > datetime.utcnow():
                to_date = datetime.utcnow()
                
            # To avoid rate limiting, wait for a while before querying the next month
            #time.sleep(1)

            if from_date.date() >= datetime.utcnow().date():
                reached_current_date = True



if __name__ == "__main__":
    main()
