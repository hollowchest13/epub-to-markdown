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

from core.models import BookFormat
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
    max_api_retries: int,
    api_delay: int,
    expect_json: bool = False,
    batch_size: int | None = None,
    batch_index: int | None = None,
) -> list | str | None:
    for attempt in range(1, max_api_retries + 1):
        try:
            response = call_gemini_api(
                client=client,
                model=model,
                contents=contents,
                expect_json=expect_json,
            )
        except RateLimitExceeded as e:
            wait_time = 2 ** (attempt - 1) * 5
            logger.warning(
                "Attempt %s/%s: Rate limit hit, batch %s. Waiting %ss. Error: %s",
                attempt,
                max_api_retries,
                batch_index,
                wait_time,
                e,
            )
            if attempt == max_api_retries:
                raise
            time.sleep(wait_time)
            continue

        except Exception as e:  # noqa: BLE001
            wait_time = 2 ** (attempt - 1) * 3
            logger.warning(
                "Attempt %s/%s: API error: %s, batch %s. Waiting %ss.",
                attempt,
                max_api_retries,
                e,
                batch_index,
                wait_time,
            )
            if attempt == max_api_retries:
                break
            time.sleep(wait_time)
            continue

        if expect_json:
            if not isinstance(response, list):
                logger.warning(
                    "Attempt %s/%s: expected list, got %s. Batch %s.",
                    attempt,
                    max_api_retries,
                    type(response),
                    batch_index,
                )
                time.sleep(api_delay)
                continue

            if batch_size is not None and len(response) != batch_size:
                logger.warning(
                    "Attempt %s/%s: response length %s != batch size %s. Batch %s.",
                    attempt,
                    max_api_retries,
                    len(response),
                    batch_size,
                    batch_index,
                )
                time.sleep(api_delay)
                continue
        else:
            if not isinstance(response, str):
                logger.warning(
                    "Attempt %s/%s: expected str, got %s. Batch %s.",
                    attempt,
                    max_api_retries,
                    type(response),
                    batch_index,
                )
                time.sleep(api_delay)
                continue
        return response

    return None


def images_to_md(
    *,
    file_name: str,
    client,
    model,
    prompt_text: str,
    api_delay: int,
    max_api_retries: int,
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

        formated_prompt_text = prompt_text.format(batch_size=batch_size)

        contents.append(formated_prompt_text)

        result = fetch_batch_with_retry(
            client=client,
            model=model,
            contents=contents,
            batch_size=len(batch),
            api_delay=api_delay,
            batch_index=i,
            max_api_retries=max_api_retries,
            expect_json=True,
        )

        if result is None:
            logger.error(
                "Batch %s: failed to receive a valid response after %s attempt(s). Batch skipped.",
                i,
                max_api_retries,
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
        time.sleep(api_delay)

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


def get_json_data(json_file: Path, default_data: dict[str, str]) -> dict[str, Any]:
    try:
        if not json_file.exists():
            json_file.write_text(
                json.dumps(default_data, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        return json.loads(json_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read settings file: %s", e)
    return default_data


def is_supported(file_path: str | Path) -> bool:
    suffix = Path(file_path).suffix.lower()
    allowed = {fmt.value for fmt in BookFormat}
    return suffix in allowed


def filter_supported_files(files: list[Path]) -> list[Path]:
    result = []
    for file in files:
        if is_supported(file):
            result.append(file)
        else:
            logger.warning("Skipping unsupported file: %s", file.name)
    return result
