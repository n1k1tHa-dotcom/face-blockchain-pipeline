from pathlib import Path
import cv2


def detect_and_crop_face(image_path: str, output_path: str = "face_crop.jpg") -> str:
    image_file = Path(image_path)

    if not image_file.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    image = cv2.imread(str(image_file))
    if image is None:
        raise ValueError("The input file is not a readable image.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)

    if detector.empty():
        raise RuntimeError("OpenCV face detector could not be loaded.")

    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        raise ValueError("No front-facing face was detected in the input image.")

    x, y, w, h = max(faces, key=lambda face: face[2] * face[3])

    padding = int(0.20 * max(w, h))
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(image.shape[1], x + w + padding)
    y2 = min(image.shape[0], y + h + padding)

    face_crop = image[y1:y2, x1:x2]

    if not cv2.imwrite(output_path, face_crop):
        raise RuntimeError(f"Could not save cropped face to: {output_path}")

    return output_path