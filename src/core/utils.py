import hashlib
import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError

from config.config import API_DELAY, MAX_API_RETRIES
from errors.api_errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def clean_filename(*, file_path: Path):
    name = file_path.stem
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
    contents: list[Any],
    expect_json: bool = False,
) -> Any:

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
        )
        text = response.text or ""
        if not expect_json:
            return text
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        logger.info(f"Answer {len(clean)} symbols")
        return json.loads(clean)

    except ClientError as e:
        logger.exception("Unsuccessful request")
        if e.code == 400:
            raise
        if e.code == 429:
            raise RateLimitExceeded()
        if e.code == 503:
            raise

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {e}")
        raise RuntimeError("Invalid JSON response from model") from e

    raise RuntimeError("Could not get a response")


def fetch_batch_with_retry(
    *,
    client: genai.Client,
    model: str,
    contents: list,
    max_retries: int,
    expect_json: bool = False,
    batch_size: int | None = None,
    batch_index: int | None = None,
) -> list | str | None:
    for attempt in range(1, max_retries + 1):
        try:
            response = call_gemini_api(
                client=client,
                model=model,
                contents=contents,
                expect_json=expect_json,
            )
        except RateLimitExceeded as e:
            wait_time = 2 ** (attempt - 1) * 5  # Наприклад: 5с, 10с, 20с...
            logger.warning(
                "Attempt %s/%s: Rate limit hit, batch %s. Waiting %ss. Error: %s",
                attempt,
                max_retries,
                batch_index,
                wait_time,
                e,
            )
            if attempt == max_retries:
                raise
            time.sleep(wait_time)
            continue

        except Exception as e:  # noqa: BLE001
            wait_time = (
                2 ** (attempt - 1) * 3
            )  # Трохи коротша затримка для звичайних помилок
            logger.warning(
                "Attempt %s/%s: API error: %s, batch %s. Waiting %ss.",
                attempt,
                max_retries,
                e,
                batch_index,
                wait_time,
            )
            if attempt == max_retries:
                break
            time.sleep(wait_time)
            continue

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
                "Attempt %s/%s: response length %s != batch size %s. Batch %s.",
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
    *,
    file_name: str,
    client,
    model,
    img_dict: dict[str, bytes],
    batch_size: int,
    callback: Callable = lambda *args, **kwargs: None,
) -> dict[str, str]:
    items = list(img_dict.items())
    images_num = len(items)
    all_results = {}

    for i in range(0, images_num, batch_size):
        batch = items[i : i + batch_size]
        current = min(i + batch_size, images_num)
        contents = []
        for name, img_data in batch:
            contents.append(
                types.Part.from_bytes(data=img_data, mime_type="image/jpeg")
            )

        prompt_text = (
            "Task: Analyze EACH provided image separately, in the exact order they are given. "
            "Do not skip, merge, or reorder images. "
            "Classify and process each image according to these rules:\n"
            "1. DATA TABLE: Convert its full content strictly into Markdown table format.\n"
            "2. GRAPH (bar, line, pie, etc.): Provide a concise description (up to 100 words) specifying its type, main trend, and key values.\n"
            "3. DIAGRAM/SCHEME (flowchart, architecture, mind map): Provide a description (up to 100 words) explaining what it shows, its main elements, connections, and key conclusion.\n"
            "4. FORMULA/EQUATION: Convert the formula strictly into LaTeX format (e.g., using $...$ or $$...$$).\n"
            "5. DECORATIVE IMAGE (photo, illustration, spacer without data): Return exactly null.\n\n"
            f"IMPORTANT: There are exactly {len(batch)} images in this request. "
            f"Return a JSON array with EXACTLY {len(batch)} elements, one per image, "
            "in the same order as the images were provided. Never omit an element — "
            "use null for decorative images instead of skipping them.\n\n"
            "Constraints:\n"
            "- Language: Return all text, descriptions, and tables in the original document's language.\n"
            "- Output Format: Return ONLY a single valid raw JSON array, exactly like this: "
            '["markdown_table_or_description", null, "$E=mc^2$"].\n'
            "- CRITICAL: Do not include any introductory text, explanations, notes, or markdown code block fences (like ```json or ```). Only the raw JSON array."
        )
        contents.append(prompt_text)

        result = fetch_batch_with_retry(
            client=client,
            model=model,
            contents=contents,
            batch_size=len(batch),
            batch_index=i,
            max_retries=MAX_API_RETRIES,
            expect_json=True,
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
        callback(
            current=current,
            total=images_num,
            text=f"{file_name} images {current}/{images_num}",
        )

        logger.info(
            "Processed %s з %s images", min(i + batch_size, images_num), images_num
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
