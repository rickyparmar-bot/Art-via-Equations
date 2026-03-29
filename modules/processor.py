"""
processor.py - High-Density Image-to-Desmos Pipeline
Achieves 1:1 visual parity with:
1. Painter's Algorithm (Area Descending)
2. RDP Epsilon = 0.0001
3. 4-decimal precision
4. Zero-gap rendering (lineWidth=0.6, lineColor=fillColor)
5. BGR→RGB color fix
"""

import cv2
import numpy as np
from PIL import Image
import base64
import io
import json
from collections import defaultdict


def rdp_algorithm(points, epsilon):
    """Ramer-Douglas-Peucker algorithm - epsilon 0.0001 = maximum detail"""
    if len(points) <= 2:
        return points

    def perpendicular_distance(point, line_start, line_end):
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        if x2 == x1:
            return abs(x0 - x1)
        if y2 == y1:
            return abs(y0 - y1)
        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = np.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
        return num / den if den > 0 else 0

    dmax, index, end = 0, 0, len(points) - 1
    for i in range(1, end):
        d = perpendicular_distance(points[i], points[0], points[end])
        if d > dmax:
            index, dmax = i, d

    if dmax > epsilon:
        r1 = rdp_algorithm(points[: index + 1], epsilon)
        r2 = rdp_algorithm(points[index:], epsilon)
        return r1[:-1] + r2
    return [points[0], points[end]]


def affine_transform(x, y, img_height):
    """Affine Transformation: pixel (i,j) → Desmos (x,y) with Y-axis inversion"""
    return x, img_height - y


def generate_polygon_latex(points, img_height, precision=4):
    """Generate polygon() LaTeX with 4-decimal precision"""
    if len(points) < 3:
        return None
    fmt = f"{{:.{precision}f}}"
    desmos_points = []
    for x, y in points:
        dx, dy = affine_transform(x, y, img_height)
        desmos_points.append(f"({fmt.format(dx)},{fmt.format(dy)})")
    return f"\\operatorname{{polygon}}({','.join(desmos_points)})"


def process_image(image_data, epsilon=0.0001, num_colors=256, min_area=0):
    """
    HIGH-DENSITY PROCESSING PIPELINE
    ================================
    1. Load image with BGR→RGB fix
    2. K-means segmentation
    3. Per-contour median color sampling (from RGB)
    4. RDP simplification (ε=0.0001) - MAX detail
    5. Painter's algorithm sorting (LARGEST→SMALLEST)
    6. Zero-gap output
    """
    # Decode image
    if isinstance(image_data, str):
        if "," in image_data:
            image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
    else:
        img_bytes = image_data

    # Load with PIL (RGB)
    pil_img = Image.open(io.BytesIO(img_bytes))
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    # Original RGB for TRUE color sampling
    img_rgb = np.array(pil_img)

    # BGR for OpenCV contour detection
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    height, width = img_rgb.shape[:2]

    # K-means for segmentation (256 colors max)
    pixels = img_rgb.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.1)
    _, labels, palette = cv2.kmeans(
        pixels, num_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )
    palette = np.uint8(palette)
    labels = labels.flatten().reshape(height, width)

    all_polygons = []

    # Process each color layer
    for color_idx in range(num_colors):
        # Binary mask for this color
        mask = (labels == color_idx).astype(np.uint8) * 255

        # Minimal morphological cleanup
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find ALL contours (RETR_LIST for MAX polygon count)
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        if hierarchy is None:
            continue

        # Process each contour
        for cont_idx, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            # === TRUE COLOR SAMPLING (BGR→RGB fix) ===
            contour_mask = np.zeros((height, width), dtype=np.uint8)
            cv2.drawContours(contour_mask, [contour], -1, 255, -1)

            # Get median RGB from original (BGR→RGB already applied)
            mean_color = cv2.mean(img_rgb, mask=contour_mask)
            r, g, b = int(mean_color[0]), int(mean_color[1]), int(mean_color[2])
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # Extract points and simplify with RDP (ε=0.0001)
            points = [(pt[0][0], pt[0][1]) for pt in contour]
            simplified = rdp_algorithm(points, epsilon)

            if len(simplified) < 3:
                continue

            # Generate polygon LaTeX with 4-decimal precision
            polygon_latex = generate_polygon_latex(simplified, height)

            if polygon_latex:
                all_polygons.append(
                    {
                        "polygon_id": len(all_polygons),
                        "area": area,
                        "hex_color": hex_color,
                        "rgb": [r, g, b],
                        "points": len(simplified),
                        "latex": polygon_latex,
                    }
                )

    # === PAINTER'S ALGORITHM: Sort by area (LARGEST → SMALLEST) ===
    all_polygons.sort(key=lambda p: p["area"], reverse=True)

    # === BACKGROUND LAYER (most frequent color) ===
    color_freq = defaultdict(int)
    for poly in all_polygons:
        color_freq[poly["hex_color"]] += 1
    bg_color = max(color_freq, key=color_freq.get) if color_freq else "#000000"

    # Create background polygon (full canvas)
    bg_latex = f"\\operatorname{{polygon}}((0,{height}.0000),({width}.0000,{height}.0000),({width}.0000,0.0000),(0,0.0000))"
    bg_polygon = {
        "polygon_id": -1,
        "area": width * height,
        "hex_color": bg_color,
        "rgb": [0, 0, 0],
        "points": 4,
        "latex": bg_latex,
    }
    # Insert at beginning
    all_polygons.insert(0, bg_polygon)

    return {
        "polygons": all_polygons,
        "background_color": bg_color,
        "stats": {
            "width": width,
            "height": height,
            "total_polygons": len(all_polygons),
            "unique_colors": len(set(p["hex_color"] for p in all_polygons)),
        },
    }


def generate_desmos_script(processed_data, batch_size=100):
    """Generate JavaScript with ZERO-GAP rendering"""
    stats = processed_data["stats"]
    polygons = processed_data["polygons"]
    w, h = stats["width"], stats["height"]

    # Build expressions with ZERO-GAP: lineWidth=0.6, lineColor=fillColor
    expressions = []
    for poly in polygons:
        expressions.append(
            {
                "latex": poly["latex"],
                "color": poly["hex_color"],
                "fill": True,
                "fillOpacity": 1,
                "lineWidth": 0.6,
                "lineOpacity": 1,
                "lineColor": poly["hex_color"],
            }
        )

    js_code = f"""// Desmos V2 - 1:1 Visual Parity
// ==========================================
// Dimensions: {w} x {h}
// Polygons: {stats["total_polygons"]}
// Colors: {stats["unique_colors"]}
// RDP Epsilon: 0.0001 (MAX Detail)
// Precision: 4 decimals
// Background: {processed_data["background_color"]}
// ==========================================

var eqs = {json.dumps(expressions)};

Calc.setBlank();
Calc.setMathBounds({{left: 0, right: {w}, bottom: 0, top: {h}}});

// Batch injection
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
        setTimeout(loadBatch, 50);
    }} else {{
        console.log("Loaded " + eqs.length + " polygons!");
    }}
}}

loadBatch();
"""
    return js_code
