from pydantic import BaseModel


class FeatureNotEnabledResponse(BaseModel):
    """
    Response when a feature is not enabled
    """

    feature: str
    message: str


class PagerDataResponse(BaseModel):
    """
    Pager data response
    """

    platform: str
    data: list | dict
    ts: str


class SuccessResponse(BaseModel):
    """
    Generic success response
    """

    result: str
    message: str
