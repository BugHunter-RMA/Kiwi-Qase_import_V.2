# kiwi/attachments.py
# Downloads attachments from Kiwi and uploads them to Qase.
# Kiwi images are embedded inline in step text as markdown:
#   ![filename.png](/uploads/attachments/auth_user/{uid}/filename.png)
# This module:
#   1. Detects image refs in step text
#   2. Downloads each image from Kiwi (uploads are publicly accessible)
#   3. Uploads to Qase as attachment
#   4. Strips image markdown from text
#   5. Returns (clean_text, [hash1, hash2, ...])

import re
import requests
from pathlib import Path


# Regex to find markdown images: ![alt](url)
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\((/uploads/[^)]+)\)')


def extract_image_urls(text):
    """Return list of (alt, relative_url) found in text."""
    return IMAGE_RE.findall(text or "")


def strip_images(text):
    """Remove image markdown from text, return clean string."""
    cleaned = IMAGE_RE.sub("", text or "")
    # Clean up any double blank lines left after removal
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def download_image(kiwi_base_url, relative_url):
    """
    Download image bytes from Kiwi.
    Kiwi uploads are publicly accessible — no auth needed.
    """
    url = kiwi_base_url.rstrip("/") + relative_url
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content, Path(relative_url).name


def upload_to_qase(project_code, filename, file_bytes, qase_headers):
    """
    Upload file to Qase.
    Returns attachment hash string.
    """
    # Qase requires multipart/form-data — drop Content-Type from headers
    headers = {k: v for k, v in qase_headers.items() if k != "Content-Type"}

    r = requests.post(
        f"https://api.qase.io/v1/attachment/{project_code}",
        headers=headers,
        files={"file": (filename, file_bytes)},
        timeout=60
    )
    r.raise_for_status()
    result = r.json()

    # Response: {"status": true, "result": [{"hash": "...", ...}]}
    attachments = result.get("result", {})
    if isinstance(attachments, list) and attachments:
        return attachments[0].get("hash")
    if isinstance(attachments, dict):
        return attachments.get("hash")
    raise ValueError(f"Unexpected Qase attachment response: {result}")


def migrate_step_attachments(step_text, kiwi_base_url, project_code, qase_headers):
    """
    For a given step text:
    - Find all embedded images
    - Download from Kiwi (no auth required)
    - Upload to Qase
    - Strip image markdown from text
    - Return (clean_text, [hash1, hash2, ...])
    """
    images = extract_image_urls(step_text)
    hashes = []

    for alt, relative_url in images:
        try:
            file_bytes, filename = download_image(kiwi_base_url, relative_url)
            hash_ = upload_to_qase(project_code, filename, file_bytes, qase_headers)
            hashes.append(hash_)
            print(f"    📎 Uploaded: {filename} -> {hash_[:12]}...")
        except Exception as e:
            print(f"    ⚠️  Failed to migrate attachment {relative_url}: {e}")

    clean_text = strip_images(step_text)
    return clean_text, hashes
