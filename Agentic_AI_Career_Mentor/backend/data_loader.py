"""
data_loader.py
--------------
Loads career roles dataset from a JSON file.
"""

import json
import os


REQUIRED_ROLE_FIELDS = {
    "skills": list,
    "domain": str,
    "required_degree": list,
    "education_level": str,
    "description": str,
    "roadmap": list,
}


def load_roles(filepath: str = None) -> dict:
    """
    Load the career roles dataset from a JSON file.

    Args:
        filepath: Path to the JSON file. Defaults to 'data/roles_dataset.json'.

    Returns:
        A dictionary containing all career roles and their details.

    Raises:
        FileNotFoundError: If the dataset file is not found.
        ValueError: If the JSON file is invalid.
    """
    if filepath is None:
        # Resolve path relative to this file's location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "data", "roles_dataset.json")

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dataset not found at '{filepath}'. "
            "Make sure 'data/roles_dataset.json' exists in the project root."
        )

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            roles = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in dataset file: {e}")

    if not roles:
        raise ValueError("Dataset is empty. Please add career roles to the JSON file.")

    for role_name, role_data in roles.items():
        for field_name, field_type in REQUIRED_ROLE_FIELDS.items():
            if field_name not in role_data:
                raise ValueError(
                    f"Role '{role_name}' is missing required field '{field_name}' in roles_dataset.json."
                )
            if not isinstance(role_data[field_name], field_type):
                raise ValueError(
                    f"Role '{role_name}' field '{field_name}' must be of type {field_type.__name__}."
                )

    return roles


def get_all_domains(roles: dict) -> list:
    """
    Extract unique domains from the roles dataset.

    Args:
        roles: The roles dictionary loaded by load_roles().

    Returns:
        A sorted list of unique domain names.
    """
    domains = {role_data["domain"] for role_data in roles.values()}
    return sorted(list(domains))


def get_roles_by_domain(roles: dict, domain: str) -> dict:
    """
    Filter roles by a specific domain.

    Args:
        roles: The full roles dictionary.
        domain: Domain name to filter by (e.g., 'Technology').

    Returns:
        A dictionary of roles belonging to the given domain.
    """
    return {
        role_name: role_data
        for role_name, role_data in roles.items()
        if role_data.get("domain", "").lower() == domain.lower()
    }
