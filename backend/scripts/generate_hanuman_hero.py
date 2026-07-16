"""Generate a stunning photorealistic Hanumanji-carrying-Sanjeevini image
via Gemini Nano Banana and save it into the frontend public folder.

Run once from CLI:
  cd /app/backend && python scripts/generate_hanuman_hero.py
"""
import asyncio, os, base64, sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure /app/backend is importable and .env is loaded
sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

PROMPT = (
    "Photorealistic epic cinematic illustration of Lord Hanuman flying across "
    "a moonlit indigo-and-violet night sky at dawn, his powerful right arm "
    "extended forward, his LEFT hand raised high above his head effortlessly "
    "carrying an enormous glowing Sanjeevini mountain filled with luminescent "
    "green medicinal herbs that emit a soft golden-green radiance. Hanuman "
    "wears a saffron-red dhoti with gold trim, a jewelled golden crown, and a "
    "flowing crimson cape trailing behind him from the speed. His fur is a "
    "deep saffron-orange with dramatic side-lighting, his expression noble, "
    "determined, and serene, forehead marked with a bold red vermillion tilak. "
    "A long powerful tail curls majestically upward behind him. Speed streaks "
    "of golden light trail behind, wispy silver clouds swirl below him, tiny "
    "sparkling stars fleck the sky, and a giant softly-glowing full moon "
    "hovers on the right. Rich saturated colors, dramatic rim lighting, "
    "highly detailed textures, mythological Indian art in the style of "
    "Raja Ravi Varma meets modern cinematic concept art. 16:9 landscape "
    "composition, banner aspect ratio, no text, no watermarks, no borders."
)


async def main():
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        print("ERROR: EMERGENT_LLM_KEY not set in /app/backend/.env")
        sys.exit(1)

    chat = LlmChat(
        api_key=api_key,
        session_id="hanuman-hero-banner",
        system_message="You are an expert cinematic illustration generator.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])

    print("Generating image via Nano Banana...")
    text, images = await chat.send_message_multimodal_response(UserMessage(text=PROMPT))
    print(f"Text: {text[:200] if text else '(none)'}")
    if not images:
        print("ERROR: No image returned by Gemini.")
        sys.exit(2)

    out_dir = Path("/app/frontend/public")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "hanuman-sanjeevini.png"

    img_bytes = base64.b64decode(images[0]["data"])
    out.write_bytes(img_bytes)
    print(f"Saved {out} ({len(img_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
