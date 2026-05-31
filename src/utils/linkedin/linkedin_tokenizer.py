import os
import requests
from dotenv import load_dotenv
load_dotenv()

class LinkedInTokenizer:
     def __init__(self,):
          self.client_id = os.getenv("LINKEDIN_CLIENT_ID")
          self.access_token = None
          self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
          self.headers = None

     def get_token(self):

          url = "https://www.linkedin.com/oauth/v2/accessToken"
          data = {
               'grant_type': 'client_credentials',
               'client_id': self.client_id,
               'client_secret': self.client_secret,

          }
          response = requests.post(url, data=data)
          if response.status_code == 200:
               self.access_token = response.json().get('access_token')
               self.headers = {'Authorization': f'Bearer {self.access_token}'}
          else:
               raise Exception(f"Failed to get access token: {response.text}")
