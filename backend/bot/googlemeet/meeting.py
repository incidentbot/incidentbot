from __future__ import print_function

import datetime
import time
import logging
import config
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleMeet:
    """
    Creates a calendar event and returns the Google Meet link, phone number and pin
    """

    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar.events']
        self.service_account_file = config.google_service_account_secret
        self.meeting_info = {}


    def create_meeting(self):

        try:
            service_account_info = json.load(open(self.service_account_file))
            credentials = service_account.Credentials.from_service_account_info(service_account_info,scopes=self.scopes)
            delegated_credentials = credentials.with_subject(config.google_account_email)
            
            service = build('calendar', 'v3', credentials=delegated_credentials, always_use_jwt_access=False)

            # Call the Calendar API
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            today = datetime.date.today()

            event = {
            # The calendar event is merely a placeholder for generating a meeting link since we don't have access to the Google Meet API
            'summary': str(today)+'-placeholder-meeting-title',
            'location': 'Virtual',
            'description': 'Incident troubleshooting',
            'start': {
                'dateTime': now,
                'timeZone': 'America/Chicago',
            },
            'end': {
                'dateTime': now,
                'timeZone': 'America/Chicago',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
                ],

            },
            'conferenceData': {
                'createRequest': {
                    'requestId': '12355',
                   'conferenceSolutionKey': {
                   'type': 'hangoutsMeet'
                },
               }
            },
            'visibility': 'public',
            'guestsCanModify': False
            }

            print("Creating event")
            event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion = 1).execute()

            print(f'Event created: {event.get("hangoutLink")}')
            self.meeting_info.update({"hangout_link": event.get("hangoutLink")})
            self.meeting_info.update({"meeting_id": event.get("id")})

            for details in event.get("conferenceData")["entryPoints"]:
                if details["entryPointType"] == "phone":
                    print(f'{details["uri"]}' +'\npin: '+ details["pin"])
                    self.meeting_info.update({"phone_number":details["uri"]})
                    self.meeting_info.update({"pin":details["pin"]})

        except HttpError as error:
            print('An error occurred: %s' % error)


    def delete_meeting(self):

        service_account_info = json.load(open(self.service_account_file))
        credentials = service_account.Credentials.from_service_account_info(service_account_info,scopes=self.scopes)
        delegated_credentials = credentials.with_subject(config.google_account_email)
        service = build('calendar', 'v3', credentials=delegated_credentials)
        service.events().delete(calendarId='primary', eventId=self.meeting_info["meeting_id"]).execute()


