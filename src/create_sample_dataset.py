"""
Synthetic Indian Traffic Sign Dataset Generator
Generates realistic geometric traffic signs on synthetic road/outdoor backgrounds
with 100% compliant YOLOv8 normalized bounding box annotations across 15 classes.
Useful for dry-running the training pipeline, testing data validation, and Colab workflows
before full dataset archives are downloaded.
"""

import os
import math
import random
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CLASSES = [
    "Stop", "No Entry", "Speed Limit 20", "Speed Limit 40", "Speed Limit 60",
    "Speed Limit 80", "Give Way", "School Ahead", "Pedestrian Crossing",
    "Left Turn", "Right Turn", "U-Turn", "Horn Prohibited", "Parking", "Dangerous Curve"
]

def create_background(width=640, height=640):
    """Creates outdoor / road background with gradients and noise."""
    bg = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(bg)
    
    # Sky / upper horizon
    sky_color = (random.randint(110, 180), random.randint(150, 210), random.randint(210, 255))
    road_color = (random.randint(50, 80), random.randint(55, 85), random.randint(60, 90))
    horizon_y = random.randint(int(height * 0.35), int(height * 0.55))
    
    draw.rectangle([(0, 0), (width, horizon_y)], fill=sky_color)
    draw.rectangle([(0, horizon_y), (width, height)], fill=road_color)
    
    # Road markings or roadside greenery
    curb_color = (random.randint(30, 70), random.randint(90, 140), random.randint(30, 70))
    draw.rectangle([(0, horizon_y - 20), (width, horizon_y + 40)], fill=curb_color)
    
    return bg

def draw_sign_patch(class_id, size=140):
    """Renders high-quality traffic sign patch for a specific class ID."""
    patch = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(patch)
    pad = 8
    
    # Colors
    RED = (210, 30, 30, 255)
    WHITE = (250, 250, 250, 255)
    BLUE = (20, 80, 210, 255)
    BLACK = (20, 20, 20, 255)
    YELLOW = (245, 195, 20, 255)
    
    # 0: Stop (Red Octagon)
    if class_id == 0:
        center = size / 2
        radius = (size - 2 * pad) / 2
        angles = [i * (2 * math.pi / 8) + (math.pi / 8) for i in range(8)]
        pts = [(center + radius * math.cos(a), center + radius * math.sin(a)) for a in angles]
        draw.polygon(pts, fill=RED)
        # Inner white border
        inner_pts = [(center + (radius - 6) * math.cos(a), center + (radius - 6) * math.sin(a)) for a in angles]
        draw.polygon(inner_pts, outline=WHITE, width=4)
        draw.text((center - 24, center - 12), "STOP", fill=WHITE)
        
    # 1: No Entry (Red Circle with white horizontal bar)
    elif class_id == 1:
        draw.ellipse([(pad, pad), (size - pad, size - pad)], fill=RED)
        bar_h = size * 0.18
        draw.rectangle([(pad * 2, size/2 - bar_h/2), (size - pad * 2, size/2 + bar_h/2)], fill=WHITE)
        
    # 2..5: Speed Limits 20, 40, 60, 80 (Red Circle, White inside, Black numbers)
    elif class_id in [2, 3, 4, 5]:
        speed = ["20", "40", "60", "80"][class_id - 2]
        draw.ellipse([(pad, pad), (size - pad, size - pad)], fill=WHITE, outline=RED, width=12)
        draw.text((size/2 - 16, size/2 - 12), speed, fill=BLACK)

    # 6: Give Way (Inverted Red Triangle, White inside)
    elif class_id == 6:
        pts = [(pad, pad), (size - pad, pad), (size/2, size - pad)]
        draw.polygon(pts, fill=WHITE, outline=RED, width=10)

    # 7: School Ahead (Yellow Triangle with pedestrian silhouettes)
    elif class_id == 7:
        pts = [(size/2, pad), (pad, size - pad), (size - pad, size - pad)]
        draw.polygon(pts, fill=YELLOW, outline=BLACK, width=6)
        draw.text((size/2 - 18, size/2), "SCH", fill=BLACK)

    # 8: Pedestrian Crossing (Blue Square or Yellow Triangle)
    elif class_id == 8:
        draw.rectangle([(pad, pad), (size - pad, size - pad)], fill=BLUE)
        # White triangle inside
        pts = [(size/2, pad + 10), (pad + 10, size - pad - 10), (size - pad - 10, size - pad - 10)]
        draw.polygon(pts, fill=WHITE)
        draw.text((size/2 - 12, size/2), "X", fill=BLACK)

    # 9, 10, 11: Left Turn, Right Turn, U-Turn (Blue Circle with white arrows or Red warning)
    elif class_id in [9, 10, 11]:
        draw.ellipse([(pad, pad), (size - pad, size - pad)], fill=BLUE)
        symbol = "<-" if class_id == 9 else ("->" if class_id == 10 else "UT")
        draw.text((size/2 - 15, size/2 - 10), symbol, fill=WHITE)

    # 12: Horn Prohibited (Red Circle with crossed-out horn)
    elif class_id == 12:
        draw.ellipse([(pad, pad), (size - pad, size - pad)], fill=WHITE, outline=RED, width=10)
        draw.text((size/2 - 16, size/2 - 10), "HORN", fill=BLACK)
        draw.line([(pad + 12, pad + 12), (size - pad - 12, size - pad - 12)], fill=RED, width=6)

    # 13: Parking (Blue Square with White 'P')
    elif class_id == 13:
        draw.rectangle([(pad, pad), (size - pad, size - pad)], fill=BLUE)
        draw.text((size/2 - 10, size/2 - 16), "P", fill=WHITE)

    # 14: Dangerous Curve (Yellow Diamond/Triangle)
    elif class_id == 14:
        pts = [(size/2, pad), (pad, size - pad), (size - pad, size - pad)]
        draw.polygon(pts, fill=YELLOW, outline=BLACK, width=6)
        draw.text((size/2 - 16, size/2), "~S~", fill=BLACK)

    return patch

def generate_sample_dataset(output_root="dataset", num_samples=150):
    """Generates synthetic dataset and writes train/valid/test images and labels."""
    root = Path(output_root)
    splits = {
        "train": int(num_samples * 0.70),
        "valid": int(num_samples * 0.15),
        "test": num_samples - int(num_samples * 0.70) - int(num_samples * 0.15)
    }

    img_w, img_h = 640, 640
    sample_counter = 0

    print(f"Generating {num_samples} synthetic Indian TSR samples across 15 classes...")

    for split_name, count in splits.items():
        img_dir = root / split_name / "images"
        lbl_dir = root / split_name / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            sample_counter += 1
            bg = create_background(img_w, img_h)
            
            # Select class
            cls_id = (sample_counter + i) % 15
            
            # Sign size between 70px and 180px
            sign_size = random.randint(80, 180)
            sign_patch = draw_sign_patch(cls_id, size=sign_size)
            
            # Random position within upper/middle canvas
            max_x = img_w - sign_size - 20
            max_y = int(img_h * 0.65) - sign_size
            min_x = 20
            min_y = 20
            
            x1 = random.randint(min_x, max(min_x + 1, max_x))
            y1 = random.randint(min_y, max(min_y + 1, max_y))
            x2 = x1 + sign_size
            y2 = y1 + sign_size
            
            # Paste sign with transparency
            bg.paste(sign_patch, (x1, y1), sign_patch)
            
            # Optional post pole
            pole_w = random.randint(4, 8)
            pole_draw = ImageDraw.Draw(bg)
            pole_color = (120, 120, 125)
            pole_draw.rectangle([(x1 + sign_size//2 - pole_w//2, y2), 
                                 (x1 + sign_size//2 + pole_w//2, min(img_h - 10, y2 + random.randint(80, 200)))], 
                                fill=pole_color)

            # Apply mild natural blur
            if random.random() > 0.5:
                bg = bg.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))

            # Save image
            img_filename = f"syn_tsr_{split_name}_{i:04d}.jpg"
            lbl_filename = f"syn_tsr_{split_name}_{i:04d}.txt"
            
            img_path = img_dir / img_filename
            lbl_path = lbl_dir / lbl_filename
            
            bg.save(img_path, quality=92)
            
            # Calculate YOLO normalized coordinates
            xc = (x1 + x2) / (2.0 * img_w)
            yc = (y1 + y2) / (2.0 * img_h)
            w = (x2 - x1) / float(img_w)
            h = (y2 - y1) / float(img_h)
            
            with open(lbl_path, "w") as f:
                f.write(f"{cls_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")

        print(f"Generated {count} samples for '{split_name}'.")

    print(f"\nSynthetic dataset generation finished successfully at {root.resolve()}!")

def main():
    parser = argparse.ArgumentParser(description="Synthetic TSR Dataset Generator")
    parser.add_argument("--num-samples", type=int, default=150, help="Total samples to generate across train/val/test")
    parser.add_argument("--output", type=str, default="dataset", help="Output directory")
    args = parser.parse_args()

    generate_sample_dataset(args.output, args.num_samples)

if __name__ == "__main__":
    main()
