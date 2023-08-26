import config


class TestConfig:
    def test_skip_logs_for_user_agent(self):
        assert config.active.options.get("skip_logs_for_user_agent") == [
            "kube-probe",
            "ELB-HealthChecker/2.0",
        ]
