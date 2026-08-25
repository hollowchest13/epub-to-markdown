import os

from dotenv import load_dotenv
from google import genai

from config.config import MODEL_VERSION

load_dotenv()


def test_large_payload():
    api_key = os.environ.get("GEMINI_API_KEY")  # або ваша назва змінної
    client = genai.Client(api_key=api_key)

    # Генеруємо великий текст, схожий за розміром на ваш батч
    large_text = "Test " * 2000

    try:
        response = client.models.generate_content(
            model=MODEL_VERSION,
            contents=large_text,
        )
        print("✅ Успішно! Великий текст пройшов.")
        print(f"Відповідь: {(response.text or '')[:100]}...")
    except Exception as e:  # noqa: BLE001
        print(f"❌ Помилка на великому тексті: {e}")


if __name__ == "__main__":
    test_large_payload()
