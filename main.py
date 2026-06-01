from granian import Granian

if __name__ == "__main__":
    Granian(
        "incidentbot.api.main:app",
        address="0.0.0.0",
        port=3000,
        interface="asgi",
        log_enabled=False,  # structlog owns all output; suppress granian's access log
    ).serve()
