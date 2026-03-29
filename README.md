# Art via Equations 🎨📐

**Art via Equations** is a high-density, zero-gap Image-to-Desmos vectorization engine. It takes any image and converts it into thousands of mathematically perfect, overlapping polygons that can be rendered directly in the [Desmos Graphing Calculator](https://www.desmos.com/calculator).

Achieve **1:1 visual parity** with your original images using pure mathematics!

## ✨ Features

- **The Painter's Algorithm:** Polygons are sorted by area (largest to smallest) so background colors and large shapes are drawn first, and fine details (like eyes and outlines) are drawn on top.
- **Zero-Gap "Caulking":** Automatically sets the Desmos `lineWidth` and `lineColor` to match the `fillColor`. This eliminates the ugly black outlines and white gaps typically seen in vectorization scripts.
- **High-Density Precision:** Capable of generating **7,000+ polygons** per image. Uses the Ramer-Douglas-Peucker (RDP) algorithm with an $\epsilon$ (epsilon) of `0.0001` to capture organic silhouettes without losing detail.
- **True Color Sampling:** Automatically corrects BGR to RGB color space and samples the median true color for every single shape.
- **Continuous Mathematical Perfection:** Outputs coordinates up to 4 decimal places for extreme accuracy.
- **Web UI Included:** Comes with a beautiful, dark-themed Flask frontend to upload images and watch the math generate in real-time.

## 🚀 Getting Started

### Prerequisites

You will need Python 3 installed on your machine.

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/rickyparmar-bot/Art-via-Equations.git
   cd Art-via-Equations
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(This installs `flask`, `flask-cors`, `opencv-python`, `numpy`, and `Pillow`)*

### Running the App

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5556
   ```

3. **Upload an Image:** Use the web interface to select an image from your computer.
4. **Tweak Settings (Optional):**
   - **Epsilon ($\epsilon$):** Controls detail. Lower = more polygons. Default is `0.0001`.
   - **Colors:** Max number of colors to segment. Default is `256`.
   - **Min Area:** Ignore tiny specs. Default is `0` (capture everything).
5. **Generate:** Click "Convert to Desmos". The app will process the image and inject the math directly into the embedded Desmos calculator!

## 🧠 How it Works

1. **Color Segmentation:** Uses K-Means clustering to separate the image into distinct color layers.
2. **Contour Detection:** Finds the edges of every single blob of color using OpenCV.
3. **Simplification:** Reduces the number of points in the curves using the RDP algorithm while maintaining the shape's integrity.
4. **Transformation:** Flips the Y-axis and applies an affine transformation to center the image on the Cartesian plane.
5. **LaTeX Generation:** Converts the coordinates into Desmos `\operatorname{polygon}(...)` syntax.
6. **Batch Injection:** Uses the Desmos API to smoothly load thousands of equations into the graph without freezing your browser.

## 📜 License

This project is open-source. Feel free to modify, distribute, and create your own mathematical masterpieces!
