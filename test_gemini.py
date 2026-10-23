
import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY is missing.")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Reply with exactly: BuildWise AI connection successful"
        )

        print("Gemini response:", response.text)

    except Exception as exc:
        print("Gemini test failed:", type(exc).__name__)
        print(str(exc)[:500])
