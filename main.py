import json
import sys
from pathlib import Path

from blockchain_module import anchor_post, network_name, verify_post
from face_module import detect_and_crop_face
from search_module import find_matching_post


def save_json(filename: str, data: dict) -> None:
    Path(filename).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_image_path>")
        sys.exit(1)

    input_image = sys.argv[1]

    print("===================================================")
    print(" FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION")
    print("===================================================")

    try:
        print("\n[1/4] Detecting and cropping face...")
        face_crop = detect_and_crop_face(input_image, "face_crop.jpg")
        print(f"SUCCESS: Face crop saved as: {face_crop}")

        print("\n[2/4] Starting real web/social-media search...")
        post_data = find_matching_post(face_crop)

        print("\nDISCOVERED MATCH:")
        print(json.dumps(post_data, indent=2, ensure_ascii=False))

        print(f"\n[3/4] Creating tamper-evident record on {network_name()}...")
        anchor_data = anchor_post(post_data)

        print("\nBLOCKCHAIN RESULT:")
        print(json.dumps(anchor_data, indent=2, ensure_ascii=False))

        print("\n[4/4] Re-verifying the same data against blockchain...")
        verification = verify_post(post_data)

        print("\nVERIFICATION RESULT:")
        print(json.dumps(verification, indent=2, ensure_ascii=False))

        full_result = {
            "input_image": input_image,
            "face_crop": face_crop,
            "discovered_post": post_data,
            "blockchain_anchor": anchor_data,
            "verification": verification,
        }

        save_json("result.json", full_result)

        if verification["verified"]:
            print("\nSUCCESS: Exact discovered-data fingerprint verified on-chain.")
            print("Saved full run output to result.json")
        else:
            print("\nFAILED: Fingerprint is not present on-chain.")
            sys.exit(1)

    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()