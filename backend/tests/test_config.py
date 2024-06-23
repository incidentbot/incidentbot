import config
import os


class TestConfig:
    def test_config_api_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.api == {
            "enabled": True
        }, "Configuration value for api settings should parse correctly"

    def test_config_digest_channel_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert (
            config.active.digest_channel == "incidents"
        ), "Configuration value for incidents digest channel should parse correctly"

    def test_config_incident_reminders_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.incident_reminders == {
            "qualifying_severities": ["sev1"],
            "rate": 30,
        }, "Configuration value for incident reminders should parse correctly"

    def test_config_integrations_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.integrations == {
            "atlassian": {
                "confluence": {
                    "auto_create_postmortem": True,
                    "space": "ENG",
                    "parent": "Postmortems",
                },
                "jira": {
                    "project": "ENG",
                    "issue_types": ["Epic", "Task"],
                    "priorities": ["High", "Low"],
                    "labels": ["incident-management"],
                    "auto_create_incident": False,
                    "auto_create_incident_type": "Subtask",
                    "status_mapping": [
                        {
                            "incident_status": "Investigating",
                            "jira_status": "Open",
                        },
                        {
                            "incident_status": "Identified",
                            "jira_status": "In Progress",
                        },
                        {
                            "incident_status": "Monitoring",
                            "jira_status": "In Review",
                        },
                        {
                            "incident_status": "Resolved",
                            "jira_status": "Done",
                        },
                    ],
                },
                "opsgenie": {"team": "oncalls"},
            },
            "pagerduty": {},
            "statuspage": {
                "url": "https://status.mydomain",
                "permissions": {"groups": ["my-slack-group"]},
            },
        }, "Configuration value for integrations should parse correctly"

    def test_config_jobs_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.jobs == {
            "scrape_for_aging_incidents": {
                "enabled": True,
                "ignore_statuses": ["test"],
            }
        }, "Configuration value for jobs should parse correctly"

    def test_config_links_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.links == [
            {
                "title": "Incident Guide",
                "url": "https://mycompany.com/incidents",
            },
            {
                "title": "My Neato Link",
                "url": "https://cool.com",
            },
        ], "Configuration value for links should parse correctly"

    def test_config_options_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.options == {
            "channel_topic": {
                "default": "This is the default incident channel topic. You can edit it in settings.",
                "set_to_meeting_link": False,
            },
            "meeting_link": "https://zoom.us",
            "skip_logs_for_user_agent": [
                "kube-probe",
                "ELB-HealthChecker/2.0",
            ],
            "timezone": "UTC",
        }, "Configuration section for options should parse correctly"

    def test_config_platform_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert (
            config.active.platform == "slack"
        ), "Configurationoption for platform should parse correctly"

    def test_config_roles_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.roles == {
            "communications_liaison": "communications_liaison",
            "incident_commander": "commander",
            "technical_lead": "technical_lead",
        }, "Configuration option for roles should parse correctly"

    def test_config_severities_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.severities == {
            "sev1": "sev1",
            "sev2": "sev2",
            "sev3": "sev3",
            "sev4": "sev4",
        }, "Configuration option for severities should parse correctly"

    def test_config_statuses_section(self):
        os.environ["IS_TEST_ENVIRONMENT"] = "true"

        assert config.active.statuses == [
            "investigating",
            "identified",
            "monitoring",
            "resolved",
        ], "Configuration option for statuses should parse correctly"
