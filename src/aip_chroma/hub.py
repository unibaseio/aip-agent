import requests
import json
import os
from io import BytesIO
from urllib.parse import urlencode

import logging
logger = logging.getLogger(__name__)

class Client:
    def __init__(self, base_url):
        self.base_url = base_url

    def initialize(self, base_url):
        if self.base_url is None:
            self.base_url = base_url

    def upload_hub(self, owner, filename, msg):
        """Upload meme message to the hub server."""
        try:
            # Create the meme structure as a dictionary
            meme_struct = {
                "Owner": owner,
                "ID": filename,
                "Message": msg
            }

            # Serialize the meme structure to JSON
            meme_struct_json = json.dumps(meme_struct)

            # Set the headers for the request
            headers = {'Content-Type': 'application/json'}
            
            # Send the POST request to the API
            response = requests.post(f"{self.base_url}/api/upload", headers=headers, data=meme_struct_json)

            # Raise an exception if the request was not successful
            response.raise_for_status()

            # Parse the response JSON into a dictionary
            res = response.json()

            # Log the upload completion
            logger.debug(f"Upload done: {res}")

            # Optionally return the response if needed
            return res

        except requests.RequestException as err:
            logger.error(f"Error during upload: {err}")
            return None

    def upload_hub_data(self, owner, filename, data):
        """Upload meme data to the hub server with multipart form."""
        try:
            # Create a BytesIO stream from the data to simulate a file-like object
            file_stream = BytesIO(data)
            
            # Prepare the files and data for the multipart request
            files = {
                'file': (filename, file_stream, 'application/octet-stream')
            }
            data = {
                'owner': owner
            }

            # Send the POST request to upload data
            response = requests.post(f"{self.base_url}/api/uploadData", files=files, data=data)

            # Raise an exception if the request was not successful
            response.raise_for_status()

            # Parse the response JSON into a dictionary
            res = response.json()

            # Log the upload completion
            logger.debug(f"Upload done: {res}")

            # Optionally return the response if needed
            return res

        except requests.RequestException as err:
            logger.error(f"Error during upload: {err}")
            return None

    def download_hub_data(self, owner, filename):
        """Download meme data from the hub server."""
        try:
            # Prepare the form data (URL-encoded parameters)
            form_data = {
                'id': filename,
                'owner': owner
            }
            
            # URL encode the form data
            encoded_form = urlencode(form_data)
            
            # Log the download action
            logger.debug(f"Downloading {owner} {filename} from hub {self.base_url}")
            
            # Send the POST request with the encoded form data
            response = requests.post(f"{self.base_url}/api/download", data=encoded_form, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            
            # Raise an exception if the request was not successful
            response.raise_for_status()
            
            # Return the response content (bytes)
            return response.content
        
        except requests.RequestException as err:
            logger.error(f"Error during download: {err}")
            return None
  
he = os.getenv('MEMBASE_HUB', 'http://54.151.130.2:8080')      
hub_client = Client(he)