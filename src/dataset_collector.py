"""
dataset_collector.py
====================
Targeted Multi-threaded Image Scraper for Authentic Indian Traffic Signs.
Uses Bing Images Async API with photo-filtering, modern user-agent, offset pagination,
and concurrent downloads.
"""

import os
import re
import ssl
import json
import time
import shutil
import urllib.request
import urllib.parse
import html as html_lib
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import io

# Disable SSL verification issues for image downloads
ssl._create_default_https_context = ssl._create_unverified_context

# 15 Canonical IRC Classes with targeted Indian search queries
CLASS_QUERIES = {
    0: {
        "name": "Stop",
        "queries": [
            "stop sign road India",
            "stop sign board traffic police India",
            "stop sign on Indian highway",
            "red stop sign board India"
        ]
    },
    1: {
        "name": "No Entry",
        "queries": [
            "no entry sign board Indian road",
            "no entry traffic sign India",
            "no entry sign post India road",
            "no entry signboard Delhi Mumbai Bangalore"
        ]
    },
    2: {
        "name": "Speed Limit 20",
        "queries": [
            "speed limit 20 sign board India road",
            "speed limit 20 kmph sign Indian road",
            "speed limit 20 sign post India",
            "20 km speed limit sign board India"
        ]
    },
    3: {
        "name": "Speed Limit 40",
        "queries": [
            "speed limit 40 sign board India road",
            "speed limit 40 kmph sign Indian highway",
            "speed limit 40 sign post India",
            "40 km speed limit sign board India"
        ]
    },
    4: {
        "name": "Speed Limit 60",
        "queries": [
            "speed limit 60 sign board India road",
            "speed limit 60 kmph sign Indian highway",
            "speed limit 60 sign post India",
            "60 km speed limit sign board India"
        ]
    },
    5: {
        "name": "Speed Limit 80",
        "queries": [
            "speed limit 80 sign board India highway",
            "speed limit 80 kmph sign Indian expressway",
            "speed limit 80 sign post India",
            "80 km speed limit sign board India"
        ]
    },
    6: {
        "name": "Give Way",
        "queries": [
            "give way sign board India road",
            "give way traffic sign Indian road",
            "yield give way sign board India",
            "triangular give way sign board Indian highway"
        ]
    },
    7: {
        "name": "School Ahead",
        "queries": [
            "school ahead sign board India road",
            "school ahead traffic sign Indian road",
            "caution school ahead sign post India",
            "school zone sign board Indian street"
        ]
    },
    8: {
        "name": "Pedestrian Crossing",
        "queries": [
            "pedestrian crossing sign board Indian road",
            "zebra crossing sign board India",
            "pedestrian crossing traffic sign Indian road",
            "pedestrian sign post India road"
        ]
    },
    9: {
        "name": "Left Turn",
        "queries": [
            "compulsory turn left sign board India",
            "sharp left turn sign board Indian road",
            "turn left traffic sign India",
            "left turn sign post Indian road"
        ]
    },
    10: {
        "name": "Right Turn",
        "queries": [
            "compulsory turn right sign board India",
            "sharp right turn sign board Indian road",
            "turn right traffic sign India",
            "right turn sign post Indian road"
        ]
    },
    11: {
        "name": "U-Turn",
        "queries": [
            "u turn sign board India",
            "u turn traffic sign Indian road",
            "u turn allowed sign board India",
            "u turn sign post Indian highway"
        ]
    },
    12: {
        "name": "Horn Prohibited",
        "queries": [
            "horn prohibited sign board India",
            "no honking sign board India road",
            "silence zone no horn sign board India",
            "no horn traffic sign India"
        ]
    },
    13: {
        "name": "Parking",
        "queries": [
            "parking sign board India road",
            "parking traffic sign blue P board India",
            "parking area sign board Indian road",
            "public parking sign board India"
        ]
    },
    14: {
        "name": "Dangerous Curve",
        "queries": [
            "dangerous curve sign board Indian road",
            "sharp curve sign board India highway",
            "hairpin bend sign board Indian hill road",
            "dangerous turn sign board India"
        ]
    }
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.8'
}


def search_bing_image_urls(query: str, target_count: int = 100) -> list:
    """Fetches direct image URLs from Bing Images Async search."""
    urls = []
    seen = set()
    offset = 0

    while len(urls) < target_count and offset < 350:
        params = urllib.parse.urlencode({
            'q': query,
            'first': offset,
            'count': 35,
            'adlt': 'moderate',
            'qft': '+filterui:photo-photo'
        })
        api_url = f"https://www.bing.com/images/async?{params}"
        try:
            req = urllib.request.Request(api_url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
            raw_links = re.findall(r'murl&quot;:&quot;(.*?)&quot;', html)
            if not raw_links:
                break

            new_links = 0
            for l in raw_links:
                clean_url = html_lib.unescape(l)
                if clean_url not in seen:
                    seen.add(clean_url)
                    urls.append(clean_url)
                    new_links += 1

            if new_links == 0:
                break

            offset += 35
            time.sleep(0.4)
        except Exception as e:
            break

    return urls


def download_single_image(url: str, dest_path: Path, timeout: int = 10) -> bool:
    """Downloads an image, validates format/integrity, and saves to dest_path."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        data = urllib.request.urlopen(req, timeout=timeout).read()
        if len(data) < 3000:  # Skip tiny / error payloads
            return False

        # Verify image can be parsed
        with Image.open(io.BytesIO(data)) as im:
            im.verify()

        # Re-open and convert to RGB/JPEG for clean format
        with Image.open(io.BytesIO(data)) as im:
            rgb_im = im.convert("RGB")
            rgb_im.save(str(dest_path), format="JPEG", quality=92)
            return True
    except Exception:
        return False


def scrape_class(class_id: int, target_count: int, output_dir: Path, max_workers: int = 8):
    class_info = CLASS_QUERIES[class_id]
    class_name = class_info["name"]
    folder_name = f"{class_id}_{class_name.replace(' ', '_').replace('-', '_')}"
    target_folder = output_dir / folder_name
    target_folder.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f"[CLASS {class_id}] {class_name} | Target: {target_count} images")
    print(f"=======================================================")

    existing_files = list(target_folder.glob("*.jpg"))
    img_idx = len(existing_files) + 1

    queries = class_info["queries"]
    all_urls = []
    seen_urls = set()

    for query in queries:
        if len(all_urls) >= target_count * 1.5:
            break
        print(f"Fetching URLs for query: '{query}'...")
        query_urls = search_bing_image_urls(query, target_count=80)
        for u in query_urls:
            if u not in seen_urls:
                seen_urls.add(u)
                all_urls.append(u)

    print(f"Total candidate URLs harvested: {len(all_urls)}")
    success_count = len(existing_files)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for url in all_urls:
            if img_idx > target_count:
                break
            dest_file = target_folder / f"{folder_name}_{img_idx:04d}.jpg"
            futures[executor.submit(download_single_image, url, dest_file)] = dest_file
            img_idx += 1

        for future in as_completed(futures):
            dest = futures[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    if dest.exists():
                        dest.unlink()
            except Exception:
                if dest.exists():
                    dest.unlink()

    print(f"[COMPLETE] Class {class_id} ({class_name}): {success_count} authentic images saved.")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Scrape authentic Indian traffic sign images.")
    parser.add_argument("--classes", type=str, default="all",
                        help="Comma-separated class IDs (e.g. '0,1,2') or 'all'")
    parser.add_argument("--limit", type=int, default=220,
                        help="Target images per class (default: 220)")
    parser.add_argument("--output_dir", type=str, default="dataset/raw_scraped",
                        help="Output directory for scraped images")
    parser.add_argument("--workers", type=int, default=8,
                        help="Concurrent download threads (default: 8)")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.classes.strip().lower() == "all":
        selected_classes = sorted(CLASS_QUERIES.keys())
    else:
        selected_classes = [int(c.strip()) for c in args.classes.split(",") if c.strip().isdigit()]

    print("=" * 65)
    print("INDIAN TRAFFIC SIGN SCRAPER (15 CANONICAL IRC CLASSES)")
    print(f"Target Classes: {selected_classes}")
    print(f"Target count: {args.limit} images per class")
    print(f"Workers: {args.workers}")
    print("=" * 65)

    summary = {}
    for cid in selected_classes:
        cnt = scrape_class(cid, args.limit, out_dir, max_workers=args.workers)
        summary[CLASS_QUERIES[cid]["name"]] = cnt

    print("\n" + "=" * 65)
    print("SCRAPING SUMMARY")
    print("=" * 65)
    total = 0
    for name, cnt in summary.items():
        print(f"  - {name:<22}: {cnt} images")
        total += cnt
    print(f"\nTotal Images Downloaded: {total}")
    print(f"Saved to: {out_dir.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
