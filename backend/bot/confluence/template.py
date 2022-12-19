import config

from bot.confluence.api import ConfluenceApi, logger

template_name = "Incident RCA Template"

api = ConfluenceApi()

tplid = next(
    item
    for item in api.get_content_templates(config.confluence_space)
    if item["name"] == template_name
)["templateId"]


def update_template(new_body: str) -> tuple[bool, str]:
    name = template_name
    body = {"storage": {"value": new_body, "representation": "storage"}}
    try:
        api.create_or_update_template(
            name=name,
            body=body,
            template_id=tplid,
            space=config.confluence_space,
        )
        return True, "success"
    except Exception as error:
        logger.error(error)
        return False, error
