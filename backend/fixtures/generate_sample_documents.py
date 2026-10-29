import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_samples():
    output_dir = Path(__file__).parent
    fixtures_file = output_dir / "sample_fixtures.json"

    with open(fixtures_file, "r") as f:
        fixtures = json.load(f)

    for item in fixtures:
        text = item["expected_transcription"]
        # Create realistic document canvas
        img = Image.new("RGB", (1200, 1600), color=(253, 252, 248))  # Slight off-white paper tint
        draw = ImageDraw.Draw(img)

        # Draw simulated handwriting text
        lines = text.split("\n")
        y = 120
        for line in lines:
            if not line.strip():
                y += 40
                continue
            draw.text((100, y), line, fill=(35, 45, 60))
            y += 42

        filename = f"{item['id']}.png"
        img_path = output_dir / filename
        img.save(img_path, format="PNG")
        print(f"Generated sample document: {img_path}")

if __name__ == "__main__":
    generate_samples()
