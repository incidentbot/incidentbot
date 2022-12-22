from bot.models.pg import Incident, IncidentLogging
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


class IncidentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Incident
        include_relationships = True
        load_instance = True


class IncidentLoggingSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = IncidentLogging
        include_relationships = True
        load_instance = True


incident_schema = IncidentSchema()
incidents_schema = IncidentSchema(many=True)
incident_logging_schema = IncidentLoggingSchema(many=True)
