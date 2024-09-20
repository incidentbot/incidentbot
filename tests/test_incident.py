from incidentbot.incident.core import Incident, IncidentRequestParameters


class TestIncident:
    def test_incident_create(self):
        self.incident_description = "The API is returning 504"
        incident = Incident(
            params=IncidentRequestParameters(
                additional_comms_channel=False,
                incident_components="Test1,Test2",
                incident_description=self.incident_description,
                incident_impact="API calls are returning errors",
                is_security_incident=False,
                private_channel=False,
                severity="sev4",
                user="mock",
            )
        )

        assert isinstance(incident, Incident)
