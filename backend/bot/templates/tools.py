from typing import Any, Dict


def parse_modal_values(body: Dict[str, Any]) -> Dict[str, Any]:
    """Return content from interactive portions of user submitted
    modals
    """
    values = body.get("view").get("state").get("values")
    result = {}
    for _, value in values.items():
        for title, content in value.items():
            block_type = content.get("type")
            match block_type:
                case "plain_text_input":
                    result[title] = content.get("value")
                case "static_select":
                    result[title] = content.get("selected_option").get("value")
    return result
