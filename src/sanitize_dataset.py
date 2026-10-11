"""
Dataset Sanitizer and Label Alignment Tool for Indian Traffic Sign Recognition (TSR).
Cleans corrupted Roboflow exports (e.g. embedded markdown comments/README headers),
filters non-sign metadata classes, and maps raw sign codes/names to 15 canonical Indian classes.

Canonical Classes (0-14):
  0: Stop
  1: No Entry
  2: Speed Limit 20
  3: Speed Limit 40
  4: Speed Limit 60
  5: Speed Limit 80
  6: Give Way
  7: School Ahead
  8: Pedestrian Crossing
  9: Left Turn
  10: Right Turn
  11: U-Turn
  12: Horn Prohibited
  13: Parking
  14: Dangerous Curve
"""

import os
import sys
import glob
import yaml
import shutil
import argparse
from pathlib import Path

CANONICAL_CLASSES = [
    "Stop",                # 0
    "No Entry",            # 1
    "Speed Limit 20",      # 2
    "Speed Limit 40",      # 3
    "Speed Limit 60",      # 4
    "Speed Limit 80",      # 5
    "Give Way",            # 6
    "School Ahead",        # 7
    "Pedestrian Crossing", # 8
    "Left Turn",           # 9
    "Right Turn",          # 10
    "U-Turn",              # 11
    "Horn Prohibited",     # 12
    "Parking",             # 13
    "Dangerous Curve"      # 14
]

# Mapping rules from raw labels / sign numbers to canonical class index (0-14)
# Handles GTSRB codes, Indian Road Congress (IRC) codes, and standard textual names.
SIGN_TO_CANONICAL = {
    # 0: Stop
    "14": 0, "stop": 0, "stop sign": 0, "stopsign": 0,
    
    # 1: No Entry
    "17": 1, "no entry": 1, "noentry": 1, "no_entry": 1, "prohibited entry": 1,
    
    # 2: Speed Limit 20
    "0": 2, "20": 2, "speed limit 20": 2, "speed limit (20km/h)": 2, "speed limit 20km/h": 2,
    
    # 3: Speed Limit 40
    "40": 3, "speed limit 40": 3, "speed limit (40km/h)": 3, "speed limit 40km/h": 3,
    
    # 4: Speed Limit 60
    "3": 4, "60": 4, "speed limit 60": 4, "speed limit (60km/h)": 4, "speed limit 60km/h": 4,
    
    # 5: Speed Limit 80
    "5": 5, "80": 5, "speed limit 80": 5, "speed limit (80km/h)": 5, "speed limit 80km/h": 5,
    
    # 6: Give Way / Yield
    "13": 6, "give way": 6, "give_way": 6, "yield": 6, "give way / yield": 6,
    
    # 7: School Ahead
    "28": 7, "school ahead": 7, "school": 7, "children crossing": 7, "children": 7,
    
    # 8: Pedestrian Crossing
    "27": 8, "pedestrian crossing": 8, "pedestrian": 8, "pedestrians": 8, "zebra crossing": 8,
    
    # 9: Left Turn
    "34": 9, "turn left ahead": 9, "turn left": 9, "left turn": 9, "compulsory left turn": 9,
    "64": 9, "72": 9, "keep left": 9, "39": 9, "left curve": 9,
    
    # 10: Right Turn
    "33": 10, "turn right ahead": 10, "turn right": 10, "right turn": 10, "compulsory right turn": 10,
    "63": 10, "73": 10, "keep right": 10, "38": 10, "right curve": 10,
    
    # 11: U-Turn
    "53": 11, "u-turn": 11, "uturn": 11, "u turn": 11, "median opening": 11,
    
    # 12: Horn Prohibited
    "60": 12, "horn prohibited": 12, "no horn": 12, "silence zone": 12, "horn_prohibited": 12,
    
    # 13: Parking
    "65": 13, "parking": 13, "parking area": 13, "parking zone": 13,
    
    # 14: Dangerous Curve / Dip
    "19": 14, "20": 14, "21": 14, "dangerous curve": 14, "double curve": 14,
    "43": 14, "44": 14, "45": 14, "46": 14, "47": 14, "48": 14, "57": 14, "dangerous dip": 14
}

JUNK_PREFIXES = (
    "*", "=", "roboflow", "the ", "for ", "to ", "traffic-sign are",
    "traffic sign -", "visit ", "annotate", "collaborate", "collect", "export",
    "understand", "use active", "speed:"
)

def is_junk_label(name: str) -> bool:
    """Detects whether a class label string is Roboflow metadata or comment noise."""
    lower = name.strip().lower()
    if any(lower.startswith(pfx) for pfx in JUNK_PREFIXES):
        return True
    if len(name.strip()) > 30:  # Comment lines are abnormally long
        return True
    return False

def find_dataset_root(search_path: Path) -> Path:
    """Finds the directory where train/val splits actually reside, handling nested folders."""
    if (search_path / "train").is_dir() or (search_path / "train/images").is_dir():
        return search_path
    
    # Check for subdirectories containing 'train'
    candidates = list(search_path.glob("**/train"))
    for cand in candidates:
        if cand.is_dir():
            return cand.parent

    return search_path

def resolve_split_paths(root: Path):
    """Accurately identifies the train, val, and test split paths under root."""
    # 1. Train
    if (root / "train" / "images").is_dir():
        train_split = "train/images"
    elif (root / "train").is_dir():
        train_split = "train"
    else:
        train_split = "train"

    # 2. Validation (checks valid/images, valid, val/images, val)
    if (root / "valid" / "images").is_dir():
        val_split = "valid/images"
    elif (root / "valid").is_dir():
        val_split = "valid"
    elif (root / "val" / "images").is_dir():
        val_split = "val/images"
    elif (root / "val").is_dir():
        val_split = "val"
    else:
        val_cands = [p for p in root.iterdir() if p.is_dir() and "val" in p.name.lower()] if root.exists() else []
        if val_cands:
            val_split = f"{val_cands[0].name}/images" if (val_cands[0] / "images").is_dir() else val_cands[0].name
        else:
            val_split = train_split

    # 3. Test
    if (root / "test" / "images").is_dir():
        test_split = "test/images"
    elif (root / "test").is_dir():
        test_split = "test"
    else:
        test_split = val_split

    return train_split, val_split, test_split

def sanitize_dataset(dataset_dir: str, output_yaml: str = None) -> str:
    """
    Sanitizes dataset directory:
      1. Identifies the real dataset root (handling nested zip extractions).
      2. Reads existing data.yaml or dataset.yaml.
      3. Creates a clean mapping from old class indices to canonical indices [0-14].
      4. Rewrites label .txt files in train/valid/test directories.
      5. Saves a clean, validated data.yaml with verified paths and nc: 15.
    """
    base_path = Path(dataset_dir).resolve()
    real_root = find_dataset_root(base_path)

    print("=" * 70)
    print(f"[SANITIZER] Processing dataset at: {real_root}")
    print("=" * 70)

    # 1. Locate original yaml
    yaml_files = list(real_root.glob("*.yaml")) + list(real_root.glob("**/*.yaml"))
    orig_yaml_path = None
    for yf in yaml_files:
        if "sanitized" not in yf.name.lower():
            orig_yaml_path = yf
            break

    orig_names = {}
    if orig_yaml_path and orig_yaml_path.exists():
        print(f"[INFO] Found source YAML: {orig_yaml_path}")
        with open(orig_yaml_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                names = data.get("names", {})
                if isinstance(names, list):
                    orig_names = {i: str(v).strip() for i, v in enumerate(names)}
                elif isinstance(names, dict):
                    orig_names = {int(k): str(v).strip() for k, v in names.items()}
            except Exception as e:
                print(f"[WARNING] Could not parse source YAML ({e}). Falling back to direct integer mapping.")
    else:
        print("[INFO] No YAML file found. Will treat existing class IDs directly as sign codes.")

    print(f"[INFO] Source dataset defined {len(orig_names)} classes.")

    # 2. Build Old Index -> Canonical Index Mapping
    index_mapping = {}
    ignored_classes = {}
    
    if orig_names:
        for old_idx, name in orig_names.items():
            if is_junk_label(name):
                ignored_classes[old_idx] = f"Junk Metadata: '{name}'"
                continue
            
            clean_key = name.strip().lower()
            target_cls = None

            if clean_key in SIGN_TO_CANONICAL:
                target_cls = SIGN_TO_CANONICAL[clean_key]
            elif clean_key.isdigit() and clean_key in SIGN_TO_CANONICAL:
                target_cls = SIGN_TO_CANONICAL[clean_key]
            
            if target_cls is not None:
                index_mapping[old_idx] = target_cls
            else:
                ignored_classes[old_idx] = f"Unmapped Class: '{name}'"
    else:
        # If no yaml names list exists, map raw integers directly
        for raw_code, target_cls in SIGN_TO_CANONICAL.items():
            if raw_code.isdigit():
                index_mapping[int(raw_code)] = target_cls

    print(f"[MAPPING] Mapped {len(index_mapping)} classes into 15 canonical Indian sign categories.")
    print(f"[MAPPING] Filtered out {len(ignored_classes)} noise/unmapped categories.")

    # 3. Locate label directories
    splits = ["train", "valid", "val", "test"]
    label_dirs = []
    for split in splits:
        for pattern in [f"{split}/labels", f"labels/{split}", f"{split}"]:
            candidate = real_root / pattern
            if candidate.is_dir() and candidate not in label_dirs:
                txts = list(candidate.glob("*.txt"))
                if txts:
                    label_dirs.append(candidate)

    if not label_dirs:
        txt_files = list(real_root.glob("**/*.txt"))
        unique_dirs = set(p.parent for p in txt_files if "labels" in p.parent.parts or any(s in p.parent.parts for s in splits))
        label_dirs = list(unique_dirs)

    print(f"[INFO] Found {len(label_dirs)} label folder(s) to sanitize.")

    # 4. Rewrite label files
    total_files = 0
    total_boxes_kept = 0
    total_boxes_removed = 0
    class_counts = {i: 0 for i in range(15)}

    for ldir in label_dirs:
        txt_files = list(ldir.glob("*.txt"))
        print(f"  -> Sanitizing {ldir.relative_to(real_root)} ({len(txt_files)} files)...")
        for txt_file in txt_files:
            total_files += 1
            new_lines = []
            with open(txt_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    old_cls = int(float(parts[0]))
                except ValueError:
                    total_boxes_removed += 1
                    continue

                if old_cls in index_mapping:
                    new_cls = index_mapping[old_cls]
                    new_lines.append(f"{new_cls} {' '.join(parts[1:])}\n")
                    class_counts[new_cls] += 1
                    total_boxes_kept += 1
                else:
                    total_boxes_removed += 1

            # Write sanitized labels back to file
            with open(txt_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    print("\n" + "=" * 70)
    print("SANITIZATION SUMMARY")
    print("=" * 70)
    print(f"Total label files processed: {total_files}")
    print(f"Total valid bounding boxes retained: {total_boxes_kept}")
    print(f"Total noise/unmapped boxes removed:  {total_boxes_removed}")
    print("\nClass Distribution Across Sanitized Dataset:")
    for cid, cname in enumerate(CANONICAL_CLASSES):
        print(f"  Class {cid:2d} | {cname:<22} : {class_counts[cid]:6d} boxes")

    # 5. Resolve verified split paths
    train_s, val_s, test_s = resolve_split_paths(real_root)
    print(f"\n[VERIFIED SPLITS] train: {train_s} | val: {val_s} | test: {test_s}")

    # 6. Generate pristine data.yaml
    if output_yaml is None:
        output_yaml = str(real_root / "data.yaml")

    clean_yaml_dict = {
        "path": str(real_root.as_posix()),
        "train": train_s,
        "val": val_s,
        "test": test_s,
        "nc": 15,
        "names": {i: name for i, name in enumerate(CANONICAL_CLASSES)}
    }

    with open(output_yaml, "w", encoding="utf-8") as f:
        yaml.dump(clean_yaml_dict, f, default_flow_style=False, sort_keys=False)

    print(f"\n[SUCCESS] Saved clean 15-class YAML configuration to: {output_yaml}")
    print("=" * 70)
    return output_yaml

def main():
    parser = argparse.ArgumentParser(description="Sanitize TSR dataset and align class IDs to 15 canonical Indian classes.")
    parser.add_argument("--dataset-dir", type=str, default="/content/dataset", help="Path to root dataset directory")
    parser.add_argument("--output-yaml", type=str, default=None, help="Path to write sanitized data.yaml")
    args = parser.parse_args()

    target_dir = args.dataset_dir
    if not os.path.exists(target_dir):
        if os.path.exists("dataset"):
            target_dir = "dataset"
        else:
            print(f"[ERROR] Target dataset directory not found at: {target_dir}")
            sys.exit(1)

    sanitize_dataset(target_dir, args.output_yaml)

if __name__ == "__main__":
    main()
