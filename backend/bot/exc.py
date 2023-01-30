class ConfigurationError(Exception):
    """Exception raised for errors in a config object

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
