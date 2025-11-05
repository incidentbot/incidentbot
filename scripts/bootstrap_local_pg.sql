CREATE ROLE incident_bot_dev LOGIN PASSWORD 'postgres';

ALTER USER incident_bot_dev WITH SUPERUSER;

CREATE DATABASE incident_bot_dev;

GRANT ALL PRIVILEGES ON DATABASE incident_bot_dev TO incident_bot_dev;