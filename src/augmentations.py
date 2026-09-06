"""
Indian Road Augmentation Engine for Traffic Sign Recognition (TSR)
Simulates authentic Indian driving challenges:
- Monsoon rain streaks & wet road reflections
- Heavy roadside tree / flyover shadow patterns
- Tropical sun glare and overexposure
- Motion blur from uneven / bumpy roads and speed
- Fine dust / smog atmospheric attenuation
Includes YOLO bounding-box coordinate tracking.
"""

import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

def add_rain(image, slant_range=(-10, 10), drop_length_range=(15, 30), drop_width=1, num_drops=500):
    """Simulates monsoon rain streaks across the frame."""
    img = image.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    slant = random.randint(*slant_range)
    
    for _ in range(num_drops):
        x = random.randint(0, w)
        y = random.randint(0, h)
        length = random.randint(*drop_length_range)
        end_x = x + slant
        end_y = y + length
        alpha_val = random.randint(140, 200)
        draw.line([(x, y), (end_x, end_y)], fill=(200, 210, 225, alpha_val), width=drop_width)
    return img

def add_shadows(image, num_polygons=2):
    """Simulates sharp tree / flyover / truck shadows common on Indian roads."""
    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size

    for _ in range(num_polygons):
        pts = [
            (random.randint(0, w), random.randint(0, h)),
            (random.randint(0, w), random.randint(0, h)),
            (random.randint(0, w), random.randint(0, h)),
            (random.randint(0, w), random.randint(0, h))
        ]
        shadow_darkness = random.randint(90, 150)
        draw.polygon(pts, fill=(20, 20, 30, shadow_darkness))

    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")

def add_sun_glare(image):
    """Simulates bright tropical midday glare overexposing parts of the sign."""
    img = image.convert("RGBA")
    glare = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glare)
    w, h = img.size

    center_x = random.randint(int(w * 0.1), int(w * 0.9))
    center_y = random.randint(int(h * 0.1), int(h * 0.5))
    radius = random.randint(80, 220)

    for r in range(radius, 0, -10):
        alpha = int(70 * (1 - r / radius))
        draw.ellipse(
            [(center_x - r, center_y - r), (center_x + r, center_y + r)],
            fill=(255, 255, 230, alpha)
        )

    combined = Image.alpha_composite(img, glare)
    return combined.convert("RGB")

def add_dust_haze(image):
    """Simulates dusty / hazy road conditions (atmospheric contrast reduction)."""
    enhancer = ImageEnhance.Contrast(image)
    low_contrast = enhancer.enhance(random.uniform(0.65, 0.85))
    
    # Warm dust tint
    tint = Image.new("RGB", image.size, (210, 180, 140))
    blended = Image.blend(low_contrast, tint, alpha=random.uniform(0.10, 0.22))
    return blended

def add_motion_blur(image):
    """Simulates camera shake or vehicle movement over speed breakers."""
    radius = random.choice([1, 2, 3])
    return image.filter(ImageFilter.GaussianBlur(radius=radius))

def apply_indian_weather_augmentations(image, bboxes=None):
    """
    Applies random combinations of Indian weather & lighting conditions.
    image: PIL.Image
    bboxes: optional list of [cls_id, xc, yc, w, h]
    """
    augmented = image.copy()
    
    # Randomly apply combinations
    if random.random() < 0.4:
        augmented = add_rain(augmented, num_drops=random.randint(300, 600))
    if random.random() < 0.4:
        augmented = add_shadows(augmented)
    if random.random() < 0.35:
        augmented = add_sun_glare(augmented)
    if random.random() < 0.3:
        augmented = add_dust_haze(augmented)
    if random.random() < 0.35:
        augmented = add_motion_blur(augmented)

    return augmented, bboxes
