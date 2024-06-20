from logger import logger
from kubernetes import client, config
from typing import Dict, List

"""
WIP
"""

config.load_kube_config()
# config.load_incluster_config()

crd_group = "extensions.incidentbot.io"
crd_namespace = "incident-bot"
crd_plural = "incidents"
crd_version = "v1alpha1"

api = client.CustomObjectsApi()


def get_incident(name: str) -> Dict:
    """Return an incident stored via the CustomResourceDefinition for Kubernetes

    Keyword arguments:
    name -- string containing the name of the Incident CRD
    """
    try:
        resource = api.get_namespaced_custom_object(
            group=crd_group,
            version=crd_version,
            name=name,
            namespace=crd_namespace,
            plural=crd_plural,
        )
    except client.exceptions.ApiException as error:
        logger.Error(
            f"Error looking for incident {name} in Kubernetes cluster: {error}"
        )

    return resource


def get_incidents() -> List[Dict]:
    """Return a list of incidents stored via the CustomResourceDefinition for Kubernetes"""
    try:
        resources = api.list_namespaced_custom_object(
            group=crd_group,
            version=crd_version,
            namespace=crd_namespace,
            plural=crd_plural,
        )

        return resources.get("items")
    except client.exceptions.ApiException as error:
        logger.Error(
            f"Error looking for incidents in Kubernetes cluster: {error}"
        )


def patch_incident(name: str, body: Dict):
    """Patch an incident stored via the CustomResourceDefinition for Kubernetes

    Keyword arguments:
    name -- string containing the name of the Incident CRD
    body -- the body for the patch operation
    """
    try:
        api.patch_namespaced_custom_object(
            group=crd_group,
            version=crd_version,
            name=name,
            namespace=crd_namespace,
            plural=crd_plural,
            body=body,
        )
    except client.exceptions.ApiException as error:
        logger.Error(
            f"Error patching incident {name} in Kubernetes cluster: {error}"
        )
