import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
LENS_ENDPOINT = "https://google.serper.dev/lens"
LENS_ATTEMPTS = 3
LENS_RETRY_DELAY_SECONDS = 3
UPLOAD_ENDPOINTS = [
    # catbox first: direct file URL with no redirects, most reliably fetchable by Google.
    "https://catbox.moe/user/api.php",
    "https://tmpfiles.org/api/v1/upload",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _upload_face_image(face_image_path: str) -> str:
    """Upload the face crop to a public host so the Lens API can fetch it."""
    for endpoint in UPLOAD_ENDPOINTS:
        try:
            with open(face_image_path, "rb") as handle:
                if "catbox.moe" in endpoint:
                    response = requests.post(
                        endpoint,
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": handle},
                        timeout=60,
                    )
                    response.raise_for_status()
                    url = response.text.strip()
                    if url.startswith("https://"):
                        return url
                else:
                    response = requests.post(
                        endpoint,
                        files={"file": handle},
                        timeout=60,
                    )
                    response.raise_for_status()
                    url = response.json()["data"]["url"]
                    # tmpfiles returns a page URL; /dl/ serves the raw image.
                    return url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
        except Exception:
            continue

    raise RuntimeError(
        "Could not upload the face crop to a public image host. "
        "Try again later or use interactive mode."
    )


def _reverse_image_search(image_url: str) -> dict:
    response = requests.post(
        LENS_ENDPOINT,
        headers={
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        },
        # The Serper Lens endpoint expects the image URL under the "url" key.
        json={"url": image_url},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _pick_match(results: dict) -> dict:
    """Pick the most relevant match from a Google Lens result set."""
    # The lens endpoint returns matches under "organic"; fall back to "images"
    # in case Serper changes the shape again.
    images = results.get("organic") or results.get("images") or []

    if not images:
        raise RuntimeError("The reverse-image search returned no visual matches.")

    for item in images:
        link = item.get("link") or ""
        image_url = item.get("imageUrl") or ""
        if link or image_url:
            return {
                "post_url": link or image_url,
                "image_url": image_url,
                "caption": (item.get("title") or "").strip(),
                "profile_url": link,
                "source": item.get("source") or item.get("domain") or "",
            }

    raise RuntimeError("The reverse-image search returned matches without usable URLs.")


def _search_with_api(face_image_path: str) -> dict:
    print("  -> Uploading face crop to a public URL...")
    public_url = _upload_face_image(face_image_path)
    print(f"  -> Uploaded: {public_url}")

    print("  -> Running Google Lens reverse-image search (Serper API)...")
    last_error = None
    for attempt in range(1, LENS_ATTEMPTS + 1):
        try:
            results = _reverse_image_search(public_url)
            match = _pick_match(results)
            print(f"  -> Top match: {match['caption'] or match['post_url']}")
            return {
                "search_method": "google_lens_reverse_image_search_via_serper",
                "post_url": match["post_url"],
                "image_url": match["image_url"],
                "caption": match["caption"],
                "profile_url": match["profile_url"],
                "source": match["source"],
                "found_at": _now(),
            }
        except Exception as error:
            last_error = error
            if attempt < LENS_ATTEMPTS:
                print(f"  ! Attempt {attempt} returned no results ({error}); retrying...")
                time.sleep(LENS_RETRY_DELAY_SECONDS)

    raise last_error


def _search_interactively(face_image_path: str) -> dict:
    print("1. Open a reverse-image/face-search provider in your browser.")
    print("2. Upload the generated face_crop.jpg file.")
    print("3. Open one genuine matching public result or post.")
    print("4. Copy its full URL.")
    print("5. Return here and paste that URL.")
    print(f"\nFace image to upload: {face_image_path}\n")

    post_url = input("Matching post/result URL: ").strip()

    if not post_url.startswith(("https://", "http://")):
        raise ValueError("URL must start with https:// or http://")

    caption = input("Visible caption/title (optional): ").strip()
    image_url = input("Matched image URL, if visible (optional): ").strip()
    profile_url = input("Profile/source URL, if visible (optional): ").strip()

    return {
        "search_method": "interactive_reverse_image_or_face_search",
        "post_url": post_url,
        "image_url": image_url,
        "caption": caption,
        "profile_url": profile_url,
        "found_at": _now(),
    }


def find_matching_post(face_image_path: str) -> dict:
    print("\nREAL SEARCH STEP")

    if SERPER_API_KEY:
        try:
            return _search_with_api(face_image_path)
        except Exception as error:
            print(f"  ! Automated search failed ({error})")
            print("  Falling back to interactive mode.\n")

    return _search_interactively(face_image_path)