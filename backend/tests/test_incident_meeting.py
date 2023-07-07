from bot.googlemeet.meeting import GoogleMeet
import config

class TestIncidentMeeting:
    def test_incident_meeting(self):

        if "googlehangout" in config.active.integrations:
            hangout = GoogleMeet()
            hangout.create_meeting()

            assert hangout.meeting_info["hangout_link"]