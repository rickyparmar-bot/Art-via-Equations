"""processor.py - Image to Desmos polygon pipeline."""

import base64
import io
import json

import cv2
import numpy as np
from PIL import Image


MAX_INTERNAL_SIDE = 1024
DESMOS_RANGE = 10.0


def _rgb_to_hex(rgb):
    r, g, b = (int(v) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _resize_for_processing(img_rgb):
    height, width = img_rgb.shape[:2]
    long_side = max(width, height)
    if long_side == 0:
        return img_rgb, 1.0

    if long_side == MAX_INTERNAL_SIDE:
        return img_rgb, 1.0

    scale = MAX_INTERNAL_SIDE / float(long_side)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(img_rgb, (new_width, new_height), interpolation=interpolation)
    return resized, scale


def _preprocess_image(img_rgb):
    resized, scale = _resize_for_processing(img_rgb)
    filtered = cv2.bilateralFilter(resized, 9, 75, 75)
    return filtered, scale


def _quantize_image(img_rgb, num_colors):
    height, width = img_rgb.shape[:2]
    pixels = img_rgb.reshape((-1, 3)).astype(np.float32)

    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        50,
        0.2,
    )
    compactness, labels, centers = cv2.kmeans(
        pixels,
        num_colors,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS,
    )

    labels = labels.reshape(height, width).astype(np.uint8)
    labels = cv2.medianBlur(labels, 3)
    centers = np.clip(np.rint(centers), 0, 255).astype(np.uint8)
    quantized = centers[labels]
    return labels, centers, quantized, compactness


def _map_point(x, y, width, height):
    scale = max(width, height) / (2.0 * DESMOS_RANGE) if max(width, height) else 1.0
    return (x - width / 2.0) / scale, (height / 2.0 - y) / scale


def _polygon_latex(points, width, height):
    if len(points) < 3:
        return None

    parts = []
    for x, y in points:
        dx, dy = _map_point(x, y, width, height)
        parts.append(f"({dx:.4f},{dy:.4f})")
    return "\\operatorname{polygon}(" + ",".join(parts) + ")"


def _expression_json(poly):
    color = poly["hex_color"]
    latex = poly["latex"]
    return (
        '{"latex":'
        + _json_escape(latex)
        + ',"color":'
        + _json_escape(color)
        + ',"fill":true,"fillOpacity":1,"lineWidth":0.6,"lineOpacity":1,"lineColor":'
        + _json_escape(color)
        + "}"
    )


def _json_escape(value):
    return json.dumps(value, separators=(",", ":"))


def process_image(image_data, epsilon=0.0001, num_colors=256, min_area=0):
    """Convert an image into quantized, centered Desmos polygons."""
    if isinstance(image_data, str):
        if "," in image_data:
            image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
    else:
        img_bytes = image_data

    num_colors = max(2, min(256, int(num_colors)))
    epsilon = float(epsilon)
    min_area = 1.0

    pil_img = Image.open(io.BytesIO(img_bytes))
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    source_rgb = np.array(pil_img)
    processed_rgb, _ = _preprocess_image(source_rgb)
    height, width = processed_rgb.shape[:2]

    labels, palette, quantized, _compactness = _quantize_image(
        processed_rgb, num_colors
    )

    polygons = []
    used_colors = set()
    for color_idx in range(len(palette)):
        mask = np.where(labels == color_idx, 255, 0).astype(np.uint8)
        if not mask.any():
            continue

        contours, _hierarchy = cv2.findContours(
            mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )

        hex_color = _rgb_to_hex(palette[color_idx])

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, max(0.0, 0.00001 * perimeter), True)
            if len(approx) < 3:
                continue

            points = [(pt[0][0], pt[0][1]) for pt in approx]
            latex = _polygon_latex(points, width, height)
            if not latex:
                continue

            used_colors.add(hex_color)
            polygons.append(
                {
                    "polygon_id": len(polygons),
                    "area": float(area),
                    "hex_color": hex_color,
                    "rgb": palette[color_idx].tolist(),
                    "points": len(points),
                    "latex": latex,
                }
            )

    polygons.sort(key=lambda p: p["area"], reverse=True)

    bg_color = _rgb_to_hex(palette[0]) if len(palette) else "#000000"
    bg_polygon = {
        "polygon_id": -1,
        "area": float(width * height),
        "hex_color": bg_color,
        "rgb": palette[0].tolist() if len(palette) else [0, 0, 0],
        "points": 4,
        "latex": _polygon_latex(
            [(0, 0), (width, 0), (width, height), (0, height)], width, height
        ),
    }
    polygons.insert(0, bg_polygon)

    stats = {
        "width": width,
        "height": height,
        "requested_colors": num_colors,
        "used_colors": len(used_colors),
        "total_polygons": len(polygons),
        "unique_colors": len(used_colors),
    }

    return {
        "polygons": polygons,
        "background_color": bg_color,
        "stats": stats,
    }


def generate_desmos_script(processed_data, batch_size=150):
    """Generate compact JS for high polygon counts."""
    stats = processed_data["stats"]
    polygons = processed_data["polygons"]

    expressions = [_expression_json(poly) for poly in polygons]
    eqs_json = "[" + ",".join(expressions) + "]"

    js_code = f"""// Desmos V2 - High Fidelity Vectorization
var eqs = {eqs_json};

Calc.setBlank();
Calc.setMathBounds({{left:-10,right:10,bottom:-10,top:10}});

var batchSize = {batch_size};
var currentBatch = 0;

function loadBatch() {{
  var start = currentBatch * batchSize;
  var end = Math.min(start + batchSize, eqs.length);
  for (var i = start; i < end; i++) {{
    eqs[i].id = 'poly_' + i;
    Calc.setExpression(eqs[i]);
  }}
  currentBatch++;
  if (end < eqs.length) {{
    setTimeout(loadBatch, 25);
  }}
}}

loadBatch();
"""
    return js_code
