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
                case "datepicker":
                    result[title] = content.get("selected_date")
                case "multi_static_select":
                    result[title] = [
                        obj.get("value")
                        for obj in content.get("selected_options")
                    ]
                case "plain_text_input":
                    result[title] = content.get("value")
                case "static_select":
                    result[title] = content.get("selected_option").get("value")
                case "timepicker":
                    result[title] = content.get("selected_time")
    return result
