import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from config import API_DELAY, MAX_API_RETRIES, OUT_OF_LIMIT_DELAY

logger = logging.getLogger(__name__)


def clean_filename(*, file_path: Path):
    # Прибираємо розширення (.pdf, .epub)
    name = file_path.stem
    # Замінюємо нижнє підкреслення на пробіли
    return name.replace("_", " ").replace("-", " ").title()


def build_metadata(*, source_file: Path, extra: dict) -> dict:
    file_size_bytes = source_file.stat().st_size

    base = {
        #  File technical data
        "source_file": source_file.name,
        "file_type": source_file.suffix.lstrip(".").lower(),
        "file_size_bytes": file_size_bytes,
        "file_hash_sha256": get_file_hash(source_file),
        "file_size_kb": round(file_size_bytes / 1024, 2),
        # Convertation
        "converted_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "converted_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    return base | extra  # merge two dictionaries


def get_file_hash(file_path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def call_gemini_api(
    *,
    client: genai.Client,
    model: str,
    max_retries: int,
    contents: list[Any],
    expect_json: bool = False,
) -> Any:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
            )
            text = response.text or ""
            if not expect_json:
                return text
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
            logger.info(f"Відповідь {len(clean)} символів")
            return json.loads(clean)

        except ClientError as e:
            logger.error(f"Attempt {attempt + 1} unsuccessful: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(OUT_OF_LIMIT_DELAY)

        except json.JSONDecodeError as e:
            logger.error(f"Attempt {attempt + 1}: Invalid JSON received: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Could not get a valid JSON response after {max_retries} attempts"
                ) from e
            time.sleep(API_DELAY)

        except Exception as e:
            if "503" in str(e):
                wait_time = 2**attempt * 5
                logger.error(f"Server overloaded, waiting {wait_time} seconds...")
                if attempt == max_retries - 1:
                    raise
                time.sleep(wait_time)
            else:
                raise

    raise RuntimeError(f"Could not get a response after {max_retries} attempts")


def _fetch_img_batch_with_retry(
    *, client, model, parts: list, batch_size: int, batch_index: int, max_retries: int
) -> list | None:
    """Sends a request to Gemini with retries until the response passes validation
    (a list of the correct length). Returns None if all attempts fail."""

    for attempt in range(1, max_retries + 1):
        response = call_gemini_api(
            client=client,
            model=model,
            max_retries=max_retries,
            contents=parts,
            expect_json=True,
        )

        if not isinstance(response, list):
            logger.warning(
                "Attempt %s/%s: expected list, got %s. Batch %s.",
                attempt,
                max_retries,
                type(response),
                batch_index,
            )
            time.sleep(API_DELAY)
            continue

        if len(response) != batch_size:
            logger.warning(
                "Attempt %s/%s: the number of elements in the response (%s) does not match the number of images in the batch (%s), batch %s.",
                attempt,
                max_retries,
                len(response),
                batch_size,
                batch_index,
            )
            time.sleep(API_DELAY)
            continue

        return response

    return None


def images_to_md(
    *, client, model, img_dict: dict[str, bytes], batch_size: int
) -> dict[str, str]:
    items = list(img_dict.items())
    images_num = len(items)
    all_results = {}

    for i in range(0, images_num, batch_size):
        batch = items[i : i + batch_size]
        parts = []
        for name, img_data in batch:
            parts.append(types.Part.from_bytes(data=img_data, mime_type="image/jpeg"))

        prompt_text = (
            "Task: Analyze EACH provided image separately, in the exact order they are given. "
            "Do not skip, merge, or reorder images. "
            "Classify and process each image according to these rules:\n"
            "1. DATA TABLE: Convert its full content strictly into Markdown table format.\n"
            "2. GRAPH (bar, line, pie, etc.): Provide a concise description (up to 100 words) specifying its type, main trend, and key values.\n"
            "3. DIAGRAM/SCHEME (flowchart, architecture, mind map): Provide a description (up to 100 words) explaining what it shows, its main elements, connections, and key conclusion.\n"
            "4. DECORATIVE IMAGE (photo, illustration, spacer without data): Return exactly null.\n\n"
            f"IMPORTANT: There are exactly {len(batch)} images in this request. "
            f"Return a JSON array with EXACTLY {len(batch)} elements, one per image, "
            "in the same order as the images were provided. Never omit an element — "
            "use null for decorative images instead of skipping them.\n\n"
            "Constraints:\n"
            "- Language: Return all text, descriptions, and tables in the original document's language.\n"
            "- Output Format: Return ONLY a single valid raw JSON array, exactly like this: "
            '["markdown_table_or_description", null, "another description"].\n'
            "- CRITICAL: Do not include any introductory text, explanations, notes, or markdown code block fences (like ```json or ```). Only the raw JSON array."
        )
        parts.append(prompt_text)

        result = _fetch_img_batch_with_retry(
            client=client,
            model=model,
            parts=parts,
            batch_size=len(batch),
            batch_index=i,
            max_retries=MAX_API_RETRIES,
        )

        if result is None:
            logger.error(
                "Batch %s: failed to receive a valid response after %s attempt(s). Batch skipped.",
                i,
                MAX_API_RETRIES,
            )
            continue

        for (name, _), desc in zip(batch, result):
            if desc is not None:
                all_results[name] = desc

        logger.info(
            "Processed %s з %s зображень", min(i + batch_size, images_num), images_num
        )
        time.sleep(API_DELAY)

    return all_results


def collect_chapters_from_text(*, text: str, chapter_min_size) -> list[tuple[str, str]]:
    pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    chapters = []
    matches = list(pattern.finditer(text))
    if matches:
        intro_text = text[: matches[0].start()].strip()
        if len(intro_text) > chapter_min_size:
            chapters.append(("Introduction", intro_text))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapter_name = match.group(2).strip()
        chapter_text = text[start:end].strip()
        if len(chapter_text) > chapter_min_size:
            chapters.append((chapter_name, chapter_text))
    if not chapters and len(text) > chapter_min_size:
        return [("Full Content", text)]
    return chapters
