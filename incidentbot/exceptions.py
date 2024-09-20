class ConfigurationError(Exception):
    """
    Exception raised for errors in a config object

    Parameters:
        message (str): explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class IndexNotFoundError(Exception):
    """
    Exception raised for index not found

    Parameters:
        message (str): explanation of the error
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class PostmortemException(Exception):
    """
    Exception raised during postmortem management

    Parameters:
        message (str): explanation of the error
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)
