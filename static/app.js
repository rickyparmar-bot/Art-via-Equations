// Desmos V2 - Frontend

let calculator;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Desmos calculator
    calculator = Desmos.GraphingCalculator(document.getElementById('calculator'), {
        keypad: false,
        toolbar: false,
        expressions: true,
        settingsMenu: false,
    });

    window.Calc = calculator;

    document.getElementById('processBtn').addEventListener('click', processImage);
    document.getElementById('fileInput').addEventListener('change', handleFileSelect);
});

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        console.log('Selected:', file.name, file.size, 'bytes');
    }
}

async function processImage() {
    const fileInput = document.getElementById('fileInput');
    const epsilon = parseFloat(document.getElementById('epsilon').value);
    const numColors = parseInt(document.getElementById('numColors').value);
    const minArea = parseInt(document.getElementById('minArea').value);
    const statsDiv = document.getElementById('stats');

    if (!fileInput.files[0]) {
        alert('Please select an image');
        return;
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = async function(e) {
        const imageData = e.target.result;
        
        statsDiv.innerHTML = '<p class="loading">Processing...</p>';

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: imageData,
                    epsilon: epsilon,
                    num_colors: numColors,
                    min_area: minArea
                })
            });

            const result = await response.json();

            if (result.success) {
                const stats = result.data.stats;
                statsDiv.innerHTML = `
                    <p class="success">
                        ✅ Generated <strong>${stats.total_polygons}</strong> polygons<br>
                        📐 Dimensions: ${stats.width} x ${stats.height}<br>
                        🎨 Colors: ${stats.unique_colors}
                    </p>
                `;

                // Execute the Desmos script
                eval(result.data.desmos_script);

                // Show completion message
                setTimeout(() => {
                    statsDiv.innerHTML += `<p class="complete">🎉 All ${stats.total_polygons} polygons loaded!</p>`;
                }, stats.total_polygons * 10);
            } else {
                statsDiv.innerHTML = `<p class="error">❌ Error: ${result.error}</p>`;
            }
        } catch (err) {
            statsDiv.innerHTML = `<p class="error">❌ Error: ${err.message}</p>`;
        }
    };

    reader.readAsDataURL(file);
}
