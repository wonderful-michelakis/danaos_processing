"""
Entity Classifier
Uses OpenAI Vision API to classify and analyze images
"""

import base64
import json
from pathlib import Path
from typing import Tuple
from openai import OpenAI
from PIL import Image
import io

from pipeline_config import EntityType, PipelineConfig

class EntityClassifier:
    """Classifies document entities using Vision API"""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.config = PipelineConfig()

    def classify_image(self, image_path: str | Path) -> Tuple[EntityType, float, dict]:
        """
        Classify an image to determine its content type

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (EntityType, confidence, metadata_dict)
        """
        # Encode image to base64
        image_data = self._encode_image(image_path)

        # Call Vision API
        response = self.client.chat.completions.create(
            model=self.config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.config.CLASSIFY_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        entity_type = EntityType(result["type"].lower())
        confidence = result.get("confidence", 0.8)

        return entity_type, confidence, result

    def extract_text(self, image_path: str | Path) -> str:
        """Extract text from an image"""
        image_data = self._encode_image(image_path)

        response = self.client.chat.completions.create(
            model=self.config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.config.EXTRACT_TEXT_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=self.config.VISION_MAX_TOKENS
        )

        return response.choices[0].message.content.strip()

    def extract_table(self, image_path: str | Path) -> str:
        """Extract table from an image and convert to YAML"""
        image_data = self._encode_image(image_path)

        response = self.client.chat.completions.create(
            model=self.config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.config.EXTRACT_TABLE_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=self.config.VISION_MAX_TOKENS
        )

        content = response.choices[0].message.content.strip()

        # Clean up if wrapped in code blocks
        if content.startswith("```yaml"):
            content = content.replace("```yaml", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        return content

    def extract_diagram(self, image_path: str | Path) -> str:
        """Extract diagram from an image and convert to Mermaid"""
        image_data = self._encode_image(image_path)

        response = self.client.chat.completions.create(
            model=self.config.VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.config.EXTRACT_DIAGRAM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=self.config.VISION_MAX_TOKENS
        )

        content = response.choices[0].message.content.strip()

        # Clean up if wrapped in code blocks
        if content.startswith("```mermaid"):
            content = content.replace("```mermaid", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        return content

    def _encode_image(self, image_path: str | Path) -> str:
        """Encode image to base64 string"""
        # Open and potentially resize image if too large
        img = Image.open(image_path)

        # Resize if larger than 2000px on either dimension
        max_size = 2000
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to JPEG and encode
        buffer = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode('utf-8')
