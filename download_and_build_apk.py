postMessage#!/usr/bin/env python3
"""
One-click downloader + builder for the Brick Bahrain (Zanabal Gaming) v7 APK.

Downloads all 9 chunk zips directly from the server, extracts them, and
reassembles the final APK — with a self-check against the known-good MD5.

Usage:
    python3 download_and_build_apk.py

Requires only Python 3 (built into every OS) — no unzip/7z/other tools needed,
no manual downloading of anything.
"""
import zipfile
import hashlib
import os
import sys
import urllib.request

EXPECTED_MD5 = "90c0163808ce0c0b858e74af1b5f6152"
EXPECTED_SIZE = 211846845
OUTPUT_NAME = "bahrain_brick_world_v7.apk"

BASE_URL = "https://base44.app/api/apps/6a4b9277df76cd820f052bca/files/mp/public/6a4b9277df76cd820f052bca/"

CHUNK_ZIP_NAMES = [
    "fe582afb3_v7_chunk_00.zip",
    "e25ea84c8_v7_chunk_01.zip",
    "5bf1a9724_v7_chunk_02.zip",
    "c1ebd2e3a_v7_chunk_03.zip",
    "1788ab636_v7_chunk_04.zip",
    "6ba672fbe_v7_chunk_05.zip",
    "0719d4745_v7_chunk_06.zip",
    "1a4678168_v7_chunk_07.zip",
    "9ced2d13f_v7_chunk_08.zip",
]

def download(name):
    url = BASE_URL + name
    print(f"  Downloading {name} ...", end=" ", flush=True)
    urllib.request.urlretrieve(url, name)
    size = os.path.getsize(name)
    print(f"{size:,} bytes")
    return size

def main():
    here = os.path.dirname(os.path.abspath(__file__)) or "."
    os.chdir(here)

    print("Step 1/2: Downloading 9 chunk files...\n")
    for name in CHUNK_ZIP_NAMES:
        if os.path.exists(name):
            print(f"  {name} already downloaded, skipping.")
            continue
        try:
            download(name)
        except Exception as e:
            print(f"\nERROR downloading {name}: {e}")
            print("Check your internet connection and re-run this script (it will skip files already downloaded).")
            sys.exit(1)

    print("\nStep 2/2: Extracting and reassembling...\n")
    hasher = hashlib.md5()
    total_bytes = 0
    with open(OUTPUT_NAME, "wb") as out:
        for i, zip_name in enumerate(CHUNK_ZIP_NAMES):
            with zipfile.ZipFile(zip_name) as zf:
                inner_names = zf.namelist()
                if len(inner_names) != 1:
                    print(f"ERROR: {zip_name} does not contain exactly 1 file: {inner_names}")
                    sys.exit(1)
                data = zf.read(inner_names[0])
                out.write(data)
                hasher.update(data)
                total_bytes += len(data)
                print(f"  [{i+1}/9] {zip_name} -> {len(data):,} bytes  (running total: {total_bytes:,})")

    final_md5 = hasher.hexdigest()
    print(f"\nReassembled file: {OUTPUT_NAME}")
    print(f"Total size: {total_bytes:,} bytes (expected {EXPECTED_SIZE:,})")
    print(f"MD5: {final_md5}")
    print(f"Expected MD5: {EXPECTED_MD5}")

    if total_bytes == EXPECTED_SIZE and final_md5 == EXPECTED_MD5:
        print("\n✅ SUCCESS — the APK downloaded and reassembled perfectly, matches the original exactly.")
        print(f"You can now install {OUTPUT_NAME} on your Android device.")
    else:
        print("\n❌ MISMATCH — something went wrong during download or extraction.")
        print("Delete the downloaded .zip files and re-run this script to try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
