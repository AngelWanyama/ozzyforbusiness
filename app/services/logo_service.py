import os
import hashlib
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont
import io

class LogoService:
    def __init__(self, output_dir: str = "/home/team/shared/generated-logos/"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Colors variants: blue, green, purple
        self.color_variants = [
            "#3b82f6", # Blue
            "#10b981", # Green
            "#8b5cf6"  # Purple
        ]

    def _get_initials(self, business_name: str) -> str:
        words = business_name.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        elif len(words) == 1:
            return words[0][:2].upper()
        return "OB"

    def _get_bg_color(self, business_name: str) -> str:
        # Business name hash to pick color
        hash_val = int(hashlib.md5(business_name.encode()).hexdigest(), 16)
        return self.color_variants[hash_val % len(self.color_variants)]

    def generate_default_logo(self, business_name: str, size: int = 256) -> bytes:
        """
        Generates a circular badge with initials.
        """
        initials = self._get_initials(business_name)
        bg_color = self._get_bg_color(business_name)
        
        # Create image with transparent background
        image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw circular background
        padding = size // 10
        draw.ellipse([padding, padding, size - padding, size - padding], fill=bg_color)
        
        # Draw text
        try:
            # Try to use a nice font if available, fallback to default
            font_size = size // 3
            # In many linux systems, DejaVuSans is available
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, font_size)
                    break
            if not font:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
            
        # Center text
        # Use textbbox if available (Pillow 9.2.0+)
        try:
            left, top, right, bottom = draw.textbbox((0, 0), initials, font=font)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            # Fallback for older Pillow
            text_width, text_height = draw.textsize(initials, font=font)
            
        draw.text(((size - text_width) // 2, (size - text_height) // 2 - (size // 20)), 
                  initials, fill="white", font=font)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        
        # Save to shared directory as requested
        file_path = os.path.join(self.output_dir, f"{business_name.replace(' ', '_')}_{size}.png")
        image.save(file_path, format="PNG")
        
        return buffer.getvalue()

    def resize_custom_logo(self, image_data: bytes, max_size: int = 256) -> bytes:
        """
        Resizes a custom logo to max dimension.
        """
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGBA if needed
        if image.mode != "RGBA":
            image = image.convert("RGBA")
            
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

logo_service = LogoService()
