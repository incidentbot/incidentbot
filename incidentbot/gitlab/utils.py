from incidentbot.logging import logger
from incidentbot.configuration.settings import settings
from typing import Dict, List, Optional
import gitlab


def get_severity_label_mapping() -> Dict[str, List[str]]:
    """
    Extracts and maps only the gitlab_labels from the settings.
    Returns: A dictionary mapping incident severity (lower) to a list of labels.
    """
    label_mapping: Dict[str, List[str]] = {}
    try:
        for mapping in settings.integrations.gitlab.severity_mapping:
            incident_severity = mapping.get("incident_severity")
            gitlab_labels = mapping.get("gitlab_labels")

            if incident_severity and isinstance(gitlab_labels, list):
                label_mapping[incident_severity.lower()] = gitlab_labels

        return label_mapping

    except AttributeError:
        logger.error("Configuration error: Label mapping settings are missing or malformed.")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error processing label mapping: {e}")
        return {}


def map_severity(severity: str) -> str:
    """
    Maps an external severity string to a GitLab-compatible severity string.
    """
    if not severity:
        return "UNKNOWN"

    try:
        mapping_dict = {
            mapping["incident_severity"].lower(): mapping["gitlab_severity"].upper()
            for mapping in settings.integrations.gitlab.severity_mapping
            if "gitlab_severity" in mapping
        }

        return mapping_dict.get(severity.lower(), "UNKNOWN")

    except AttributeError:
        logger.error("Configuration error: Severity mapping settings are missing or malformed.")
        return "UNKNOWN"
    except Exception as e:
        logger.error(f"Error processing severity mapping from settings: {e}")
        return "UNKNOWN"


def format_channel_label(channel_name: str) -> str:
    """
    Formats a channel name using the configured label template.

    Args:
        channel_name: The channel name to format

    Returns:
        Formatted label string
    """
    label_template = settings.integrations.gitlab.label_template
    if label_template:
        return label_template.format(channel_name=channel_name)
    return channel_name


def build_mapping_dict(mapping_list: list, incident_key: str) -> dict:
    """
    Builds a lookup dictionary from a mapping list.

    Args:
        mapping_list: List of mapping dictionaries
        incident_key: Key name to use for incident values (e.g., 'incident_severity', 'incident_status')

    Returns:
        Dictionary mapping incident values (lowercase) to mapping objects
    """
    try:
        return {
            item.get(incident_key, "").lower(): item
            for item in mapping_list
            if item is not None
        }
    except AttributeError:
        logger.error(f"Invalid item found in mapping list for key '{incident_key}'.")
        return {}


def find_issue_by_label(
    project,
    channel_name: str,
    issue_type: Optional[str] = None
) -> Optional[object]:
    """
    Finds a GitLab issue by channel name label.

    Args:
        project: GitLab project object
        channel_name: Channel name to search for
        issue_type: Optional issue type filter (e.g., 'incident')
        use_label_template: Whether to apply label template formatting (default: True)

    Returns:
        First matching issue or None
    """
    if not project:
        logger.error("No project provided for issue search.")
        return None

    try:
        search_label = format_channel_label(channel_name)

        search_params = {
            "labels": [search_label],
            "get_all": True
        }

        if issue_type:
            search_params["issue_type"] = issue_type

        issues = project.issues.list(**search_params)

        if not issues:
            logger.warning(f"No GitLab issue found with label {search_label}.")
            return None

        return issues[0]

    except gitlab.exceptions.GitlabListError as error:
        logger.error(f"Error listing GitLab issues by label {channel_name}: {error}")
        return None
    except Exception as error:
        logger.error(f"Unexpected error retrieving GitLab issue: {error}")
        return None


def find_issues_by_label(
    project,
    channel_name: str,
    issue_type: Optional[str] = None,
    use_label_template: bool = True
) -> list:
    """
    Finds all GitLab issues matching a channel name label.

    Args:
        project: GitLab project object
        channel_name: Channel name to search for
        issue_type: Optional issue type filter
        use_label_template: Whether to apply label template formatting (default: True)

    Returns:
        List of matching issues (empty list if none found)
    """
    if not project:
        logger.error("No project provided for issue search.")
        return []

    try:
        search_label = format_channel_label(channel_name) if use_label_template else channel_name

        search_params = {
            "labels": [search_label],
            "get_all": True
        }

        if issue_type:
            search_params["issue_type"] = issue_type

        issues = project.issues.list(**search_params)

        if not issues:
            logger.warning(f"No GitLab issues found with label {search_label}.")
            return []

        return issues

    except gitlab.exceptions.GitlabListError as error:
        logger.error(f"Error listing GitLab issues by label {channel_name}: {error}")
        return []
    except Exception as error:
        logger.error(f"Unexpected error retrieving GitLab issues: {error}")
        return []


def update_issue_labels(
    issue,
    new_labels: List[str],
    remove_scoped_prefixes: bool = True
) -> List[str]:
    """
    Updates issue labels, optionally removing existing scoped labels with the same prefix.

    Args:
        issue: GitLab issue object
        new_labels: List of labels to add
        remove_scoped_prefixes: If True, removes existing labels with same scope prefix

    Returns:
        Updated list of labels
    """
    if not new_labels:
        return issue.labels

    current_labels = issue.labels.copy()

    if remove_scoped_prefixes:
        # Extract scoped prefixes from new labels (e.g., "status" from "status::resolved")
        scoped_prefixes = {
            label.split("::")[0]
            for label in new_labels
            if "::" in label
        }

        if scoped_prefixes:
            logger.debug(f"Removing existing scoped labels with prefixes: {scoped_prefixes}")
            current_labels = [
                label for label in current_labels
                if not any(label.startswith(prefix + "::") for prefix in scoped_prefixes)
            ]

    # Combine and deduplicate
    return list(set(current_labels + new_labels))


def get_initial_status_labels() -> List[str]:
    """
    Gets the labels for the initial 'investigating' status from configuration.

    Returns:
        List of labels for investigating status, empty list if not configured
    """
    if not settings.integrations.gitlab.status_mapping:
        return []

    for mapping in settings.integrations.gitlab.status_mapping:
        if mapping.get("incident_status", "").lower() == "investigating":
            return mapping.get("gitlab_labels", [])

    return []