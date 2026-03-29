# Title: High-Density Image Vectorization and Parity Preservation using Geometric Primitives in the Desmos Coordinate System
**Author:** Ricky Parmar
**Date:** March 2026

## Abstract
This paper introduces "Art via Equations," a novel pipeline designed to vectorize high-fidelity raster images into continuous mathematical coordinate planes. By applying the Ramer-Douglas-Peucker (RDP) algorithm with sub-millimeter $\epsilon$ (epsilon) bounds alongside K-means chromatic clustering, the system parses images into 7,000+ localized geometric polygons. Furthermore, we present a solution to rendering interpolation artifacts ("white gaps") by dynamically manipulating stroke widths and matching stroke colors to fill vectors—a process we term "Zero-Gap Caulking." This methodology achieves near 1:1 visual parity when rendered via the Desmos Graphing Calculator API.

## 1. Introduction
Graphing calculators, specifically Desmos, have become an unconventional medium for digital art. Historically, this involved manually entering thousands of algebraic and parametric equations. Existing automated approaches typically trace boundaries and yield wireframe approximations (hollow silhouettes) or suffer from sub-optimal polygon layering, leading to visible rendering gaps and poor chromatic translation (e.g., the BGR-to-RGB distortion). This paper proposes a robust pipeline that solves these spatial and chromatic inaccuracies using area-sorted rendering (the Painter's Algorithm) and zero-bleed polygon construction.

## 2. Methodology

### 2.1 Color Quantization and Correction
The source raster image undergoes standard memory decoding. Since Open Source Computer Vision (OpenCV) natively processes matrices in Blue-Green-Red (BGR) formats, any sampled colors must first be corrected. We apply `cv2.cvtColor(image, cv2.COLOR_BGR2RGB)` prior to sampling. 

The image is then clustered using the K-means algorithm to group pixels into discrete color sets $C$ where $N_{colors} \le 256$.

### 2.2 Boundary Detection and RDP Simplification
For every color class, we generate a binary morphology mask. We then invoke `cv2.findContours` using the `RETR_LIST` argument to ensure both internal (nested) and external topologies are captured, completely bypassing typical region thresholds (`min_area = 0`).

The raw contour vertices are simplified using the Ramer-Douglas-Peucker (RDP) algorithm. To ensure "continuous mathematical perfection," our pipeline sets the orthogonal distance threshold ($\epsilon$) strictly to $0.0001$. This captures organic micro-details—such as eyelashes or sharp geometric vertices—without over-simplifying the silhouette.

### 2.3 Coordinates and Affine Transformation
Standard image coordinate systems originate at the top-left $(0, 0)$. Cartesian planes originate at the bottom-left. We apply a strict Affine Transformation to flip the Y-axis:
$$ (x', y') = (x, Height_{image} - y) $$
All coordinates are formatted to exactly 4 decimal places for precision constraints required by JavaScript execution environments.

### 2.4 The Painter's Algorithm (Depth Sorting)
Desmos renders equations linearly. If a background element is drawn after a foreground element, the foreground is obscured. To solve this, all generated polygons are collected into a global array and sorted by their pixel area $A$ in strictly descending order. Thus, broad environmental shapes are injected into the Desmos stack first, while fine details (like lips, highlights, and borders) are overlaid correctly.

### 2.5 Zero-Gap Caulking
The most significant visual flaw in traditional polygon vectorization is anti-aliasing interpolation, which creates $0.5$ pixel "white gaps" between perfectly aligned adjacent polygons. We solve this mathematically by exploiting the stroke property:
- The polygon interior color $C_{fill}$ is defined.
- The polygon stroke width $W$ is forcibly set to $0.6$ (up from $0$).
- The stroke color $C_{stroke}$ is explicitly mapped to match $C_{fill}$.

By bleeding the boundaries outward by exactly $0.6$ units using the identical hex string, the gaps are caulked seamlessly, eliminating artifact outlines.

## 3. Results and Performance
The pipeline was tested against standard API injection scripts.
- **Polygon Density:** Up to 7,500 individual elements resolved.
- **Visual Parity:** Reached near 1:1 similarity with the raster source, exhibiting no blue-shift and zero coordinate bleed.
- **Engine Load:** Using JavaScript asynchronous chunking (injecting batches of 100 expressions every 50ms), the system prevents the DOM thread from crashing while processing the 7,000+ payload.

## 4. Conclusion
"Art via Equations" demonstrates that with aggressive RDP thresholds, area-descending topological sorting, and stroke manipulation, graphing calculators can transcend wireframes and be used to perfectly reconstruct complex, colored raster images via pure mathematical formulas. 

## References
1. Ramer, U. (1972). *An iterative procedure for the polygonal approximation of plane curves.* Computer Graphics and Image Processing.
2. Douglas, D. & Peucker, T. (1973). *Algorithms for the reduction of the number of points required to represent a digitized line or its caricature.*
3. Open Source Computer Vision Library (OpenCV).
4. Desmos Studio API Documentation.