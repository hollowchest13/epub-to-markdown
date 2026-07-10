from pathlib import Path
from datetime import datetime
import hashlib
import re
import time
import json
from google import genai
from google.genai.errors import ClientError
from typing import Any
from google.genai import types

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_filename(*, file_path: Path):
    # Прибираємо розширення (.pdf, .epub)
    name = file_path.stem
    # Замінюємо нижнє підкреслення на пробіли
    return name.replace("_", " ").replace("-", " ").title()


def build_metadata(*, source_file: Path, extra: dict) -> dict:
    file_size_bytes = source_file.stat().st_size

    base = {
        # --- Технічні дані файлу ---
        "source_file": source_file.name,
        "file_type": source_file.suffix.lstrip(".").lower(),
        "file_size_bytes": file_size_bytes,
        "file_hash_sha256": get_file_hash(source_file),
        "file_size_kb": round(file_size_bytes / 1024, 2),
        # --- Конвертація ---
        "converted_date": datetime.now().strftime("%Y-%m-%d"),
        "converted_at": datetime.now().isoformat(),
    }

    return base | extra  # merge двох словників


def get_file_hash(file_path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_markdown(text):
    text = re.sub(r"<\?xml[^?]*\?>", "", text)
    text = re.sub(r"xml version=['\"].*?['\"]", "", text)
    text = re.sub(r"encoding=['\"]utf-8['\"][?]?", "", text)
    text = re.sub(r"\([cp]\d+\.xhtml(?:#.*?)?\)", "", text)
    text = re.sub(r"\(.*?\.html#filepos\d+\)", "", text)
    text = re.sub(r"!\[.*?\]\(images/.*?\)", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\(\#[a-z0-9]+-tbl-\d+\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def call_gemini_api(*, client: genai.Client, model: str, max_retries: int, contents: list[Any], expect_json: bool = False) -> Any:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=contents)
            text = response.text or ""
            if not expect_json:
                return text
            clean_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
            return json.loads(clean_text)
        except ClientError as e:
            logger.error(f"Attempt {attempt + 1} unsuccessful: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(60)
        except json.JSONDecodeError as e:
            logger.error(f"Attempt {attempt + 1}: Invalid JSON received: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Could not get a valid JSON response after {max_retries} attempts") from e
            time.sleep(2)
        except Exception as e:
            if "503" in str(e):
                wait_time = 2 ** attempt * 5
                logger.error(f"Server overloaded, waiting {wait_time} seconds...")
                if attempt == max_retries - 1:
                    raise
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError(f"Could not get a response after {max_retries} attempts")
def images_to_md(*,client,model, img_dict: dict[str, bytes], batch_size: int = 15) -> dict[str, str]:
    items = list(img_dict.items())
    all_results = {}

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        parts = []
        index_to_name = {}
        for idx, (name, img_data) in enumerate(batch):
            parts.append(types.Part.from_bytes(data=img_data, mime_type="image/jpeg"))
            index_to_name[idx] = name

        prompt_text = (
            "Task: Analyze EACH provided image separately by its sequence number. Do not mix up the images. "
            "Classify and process each image according to these rules:\n"
            "1. DATA TABLE: Convert its full content strictly into Markdown table format.\n"
            "2. GRAPH (bar, line, pie, etc.): Provide a concise description (up to 100 words) specifying its type, main trend, and key values.\n"
            "3. DIAGRAM/SCHEME (flowchart, architecture, mind map): Provide a description (up to 100 words) explaining what it shows, its main elements, connections, and key conclusion.\n"
            "4. DECORATIVE IMAGE (photo, illustration, spacer without data): Return exactly null.\n\n"
            "Constraints:\n"
            "- Language: Return all text, descriptions, and tables in the original document's language.\n"
            "- Output Format: Return ONLY a single valid raw JSON string where keys are sequence numbers (strings) and values are the results, exactly like this: {\"0\": \"markdown_table_or_description\", \"1\": null}.\n"
            "- CRITICAL: Do not include any introductory text, explanations, notes, or markdown code block fences (like ```json or ```). Only the raw JSON string."
        )
        parts.append(prompt_text)
        result = {}
        max_retries = 5
        call_gemini_api(client=client,model=model,max_retries=max_retries,contents=parts,expect_json=True)
        all_results.update(
            {
                index_to_name[int(idx)]: desc
                for idx, desc in result.items()
                if desc is not None
            }
        )
        time.sleep(6)

    return all_results
