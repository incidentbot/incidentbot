import json


def find_index_in_list(lst, key, value):
    """Takes a list of dictionaries and returns
    the index value if key matches.
    """
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def render_json(file, variables: dict) -> dict:
    """Reads a template file as JSON, replaces vars using a dict,
    and returns JSON
    """
    try:
        with open(file, "r") as f:
            json_data = f.read()
            for k, v in variables.items():
                json_data = json_data.replace(f"{{{k}}}", v)
    except:
        print(f"error when interpolating variables on file {file}: ")
        print(variables)
    return json.loads(json_data)
