from incidentbot.configuration.schema import Conditions
from incidentbot.configuration.settings import settings
from incidentbot.models.incident import IncidentDatabaseInterface


def evaluate(conditions: Conditions | None, record) -> bool:
    """
    Return True if all conditions in the Conditions object are satisfied
    for the given incident record. A None conditions object always passes.
    """
    if conditions is None:
        return True

    if conditions.severity_is and record.severity not in conditions.severity_is:
        return False

    if conditions.status_is and record.status not in conditions.status_is:
        return False

    if conditions.status_is_final:
        final_statuses = {
            name for name, cfg in settings.statuses.items() if cfg.final
        }
        if record.status not in final_statuses:
            return False

    if conditions.no_roles_claimed:
        participants = IncidentDatabaseInterface.list_participants(record)
        if participants:
            return False

    return True
