from bot.confluence.rca import IncidentRootCauseAnalysis
from bot.models.pg import AuditLog, IncidentLogging
from bot.slack.incident_logging import read


class TestIncidentRootCauseAnalysis:
    def test_rca(self, mocked_session):
        rca = IncidentRootCauseAnalysis(
            incident_id="mock",
            rca_title="mock",
            incident_commander="mock_incident_commander",
            technical_lead="mock_technical_lead",
            severity="low",
            severity_definition="sample severity definition for low severity",
            pinned_items=mocked_session.query(IncidentLogging)
            .filter_by(incident_id="inc-mock-test")
            .all(),
            timeline=mocked_session.query(AuditLog)
            .filter_by(incident_id="inc-mock-test")
            .one()
            .data,
        )

        assert isinstance(rca, IncidentRootCauseAnalysis)

        assert len(rca.pinned_items) == 2

        assert len(rca.timeline) == 1

        assert (
            rca._IncidentRootCauseAnalysis__generate_pinned_messages()
            == "<blockquote><p><strong>mock_user @ time - </strong> some "
            + "messaged that was pinned</p></blockquote><p /><blockquote>"
            + "<p><strong>mock_user @ time - </strong> some messaged that"
            + " was pinned</p></blockquote><p />"
        )

        assert (
            rca._IncidentRootCauseAnalysis__generate_timeline()
            == """
    <tr>
        <td>
            <p>2022-12-09T16:54:50 UTC</p>
        </td>
        <td>
            <p>Incident created.</p>
        </td>
    </tr>
    
    <tr>
        <td>
            <p>&hellip;</p>
        </td>
        <td>
            <p>&hellip;</p>
        </td>
    </tr>
    """
        )
