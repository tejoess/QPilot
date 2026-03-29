"""
backend/services/template_service/storage.py

Handles saving, listing, and resolving uploaded DOCX templates.
Templates are stored under: backend/Storage/templates/{user_id}/
"""

import os
import json
import uuid
from typing import List, Dict, Optional


TEMPLATES_BASE = os.path.join("backend", "Storage", "templates")


def _user_dir(user_id: str) -> str:
    path = os.path.join(TEMPLATES_BASE, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_template(user_id: str, file_bytes: bytes, filename: str, pattern: list, placeholders: list) -> Dict:
    """
    Save an uploaded DOCX template and its extracted metadata.
    Returns a dict with template_id, name, path, pattern.
    """
    template_id = str(uuid.uuid4())
    user_dir = _user_dir(user_id)

    # Save the DOCX file
    safe_name = filename.replace(" ", "_")
    docx_path = os.path.join(user_dir, f"{template_id}_{safe_name}")
    with open(docx_path, "wb") as f:
        f.write(file_bytes)

    # Save the metadata
    meta = {
        "template_id": template_id,
        "name": filename,
        "docx_path": docx_path,
        "pattern": pattern,
        "placeholders": placeholders,
    }
    meta_path = os.path.join(user_dir, f"{template_id}.meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta


def list_templates(user_id: str) -> List[Dict]:
    """
    List all templates for a user by reading their .meta.json files.
    """
    user_dir = _user_dir(user_id)
    templates = []
    for fname in os.listdir(user_dir):
        if fname.endswith(".meta.json"):
            with open(os.path.join(user_dir, fname)) as f:
                templates.append(json.load(f))
    return templates


def get_template_meta(user_id: str, template_id: str) -> Optional[Dict]:
    """
    Get a single template's metadata by ID.
    """
    user_dir = _user_dir(user_id)
    meta_path = os.path.join(user_dir, f"{template_id}.meta.json")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path) as f:
        return json.load(f)


def get_template_path(user_id: str, template_id: str) -> Optional[str]:
    """
    Resolve the DOCX path for a template.
    """
    meta = get_template_meta(user_id, template_id)
    if not meta:
        return None
    return meta.get("docx_path")
