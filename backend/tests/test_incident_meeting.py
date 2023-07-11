from bot.googlemeet.meeting import GoogleMeet
import os
import config

class TestIncidentMeeting:
    def test_incident_meeting(self):

        if "googlehangout" in config.active.integrations:
            hangout = GoogleMeet()
            print(os.environ["GOOGLE_SERVICE_ACCOUNT_SECRET"])
            print(config.google_service_account_secret)
            hangout.create_meeting()
            hangout.delete_meeting()

            assert hangout.meeting_info["hangout_link"]
