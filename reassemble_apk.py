#!/usr/bin/env python3
"""
Reassembles the Brick Bahrain (Zanabal Gaming) v7 APK from the 9 downloaded
chunk zip files. Run this in the SAME FOLDER where you downloaded all 9 zips.

Usage:
    python3 reassemble_apk.py

Requires only Python 3 (built into every OS) — no unzip/7z/other tools needed.
"""
import zipfile
import hashlib
import os
import sys

EXPECTED_MD5 = "90c0163808ce0c0b858e74af1b5f6152"
EXPECTED_SIZE = 211846845
OUTPUT_NAME = "bahrain_brick_world_v7.apk"

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

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    print("Looking for chunk zips in:", here)
    missing = [n for n in CHUNK_ZIP_NAMES if not os.path.exists(n)]
    if missing:
        print("\nERROR: Missing these files — download them and put them next to this script:")
        for m in missing:
            print("  -", m)
        sys.exit(1)

    print("All 9 chunk zips found. Extracting and reassembling...\n")
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
        print("\n✅ SUCCESS — the APK reassembled perfectly and matches the original exactly.")
        print(f"You can now install {OUTPUT_NAME} on your Android device.")
    else:
        print("\n❌ MISMATCH — something went wrong during download or extraction.")
        print("Please re-download all 9 zip files fresh and run this script again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
