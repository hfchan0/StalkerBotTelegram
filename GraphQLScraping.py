import requests
import os
import json
import os
from dotenv import load_dotenv

load_dotenv()
# Set up the API endpoint and authentication headers
access_token = os.getenv("TOKEN")
api_endpoint = "https://graph.instagram.com/me/media?fields=id,media_type,media_url,thumbnail_url&access_token=" + access_token

# Make a GET request to the API endpoint
response = requests.get(api_endpoint)

# Parse the response JSON data
data = json.loads(response.content)

# Iterate over all the media files and download them
for media in data['data']:
    media_url = media['media_url']
    media_id = media['id']
    media_type = media['media_type']
    media_extension = ".jpg" if media_type == "IMAGE" else ".mp4"
    media_filename = media_id + media_extension

    # Download the media file
    media_data = requests.get(media_url).content
    with open(media_filename, "wb") as f:
        f.write(media_data)
