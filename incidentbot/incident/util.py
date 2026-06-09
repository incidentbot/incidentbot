from incidentbot.exceptions import IndexNotFoundError
from incidentbot.util import gen
from typing import Any


def extract_role_owner(message_blocks: dict[Any, Any], block_id: str) -> str:
    """
    Takes message blocks and a block_id and returns information specific
    to one of the role blocks
    """
    index = gen.find_index_in_list(message_blocks, "block_id", block_id)
    if index == -1:
        raise IndexNotFoundError(f"could not find index for block_id {block_id}")

    return message_blocks[index]["text"]["text"].split("\n")[1].replace(" ", "")
