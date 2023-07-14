import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta

class GoogleMeetMeeting:
    """Creates a Google Meet meeting"""
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials = self.__generate_token()
        self.service = build('calendar', 'v3', credentials=self.credentials)

    @property
    def url(self):
        url = self.__create()
        return url

    def __create(self) -> str:
        event_start = (datetime.now() + timedelta(minutes=0)).isoformat()
        event_end = (datetime.now() + timedelta(hours=1)).isoformat()
        meeting = {
            'summary': 'Incident Discussion',
            'start': {
                'dateTime': event_start,
                'timeZone': 'Europe/Warsaw',
            },
            'end': {
                'dateTime': event_end,
                'timeZone': 'Europe/Warsaw',
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': 'sample123',
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    },
                }
            }
        }
        try:
            meeting = self.service.events().insert(calendarId='primary', body=meeting, conferenceDataVersion=1).execute()
            return meeting['hangoutLink']
        except Exception as error:
            print(f"Error creating Google Meet meeting: {error}")

    def __generate_token(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return creds

    def test_auth(self):
        token = self.__generate_token()
        if not token:
            return False
        return True
