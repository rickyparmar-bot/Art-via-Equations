let calculator;
let lastDesmosStrings = [];
let lastDesmosExpressions = [];
let lastDesmosScript = '';
let currentFile = null;
let progressTimer = null;

const STAGES = [
    { name: 'Preparing Upload...', percent: 12, detail: 'Encoding source image for the processing pipeline.' },
    { name: 'Quantizing Colors...', percent: 36, detail: 'Clustering tones into a Desmos-safe palette.' },
    { name: 'Tracing Edges...', percent: 64, detail: 'Extracting contours and building polygon paths.' },
    { name: 'Optimizing Math...', percent: 84, detail: 'Packing equations for Desmos rendering and export.' },
];

document.addEventListener('DOMContentLoaded', () => {
    calculator = Desmos.GraphingCalculator(document.getElementById('calculator'), {
        keypad: false,
        toolbar: false,
        expressions: true,
        settingsMenu: false,
    });

    window.Calc = calculator;

    document.getElementById('processBtn').addEventListener('click', processImage);
    document.getElementById('downloadBtn').addEventListener('click', downloadEquations);
    document.getElementById('copyScriptBtn').addEventListener('click', copyDesmosScript);
    document.getElementById('fileInput').addEventListener('change', (event) => handleIncomingFile(event.target.files[0]));
    window.addEventListener('resize', () => calculator.resize());

    setupDropZone();
    updateProgress('Idle', 0, 'Load an image to begin.');
    calculator.resize();
});

function setupDropZone() {
    const dropZone = document.getElementById('dropZone');

    ['dragenter', 'dragover'].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        dropZone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (event) => {
        const file = event.dataTransfer.files[0];
        if (file) {
            handleIncomingFile(file);
        }
    });
}

function handleIncomingFile(file) {
    if (!file) {
        return;
    }

    currentFile = file;
    const fileInput = document.getElementById('fileInput');
    const transfer = new DataTransfer();
    transfer.items.add(file);
    fileInput.files = transfer.files;

    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatBytes(file.size);
    drawBlurPreview(file);
    updateProgress('Ready', 6, 'Image loaded. Start the vector pipeline when ready.');
}

function drawBlurPreview(file) {
    const canvas = document.getElementById('blurPreview');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
        canvas.width = 48;
        canvas.height = 48;
        ctx.clearRect(0, 0, 48, 48);
        ctx.drawImage(img, 0, 0, 48, 48);
    };
    img.src = URL.createObjectURL(file);
}

async function processImage() {
    const fileInput = document.getElementById('fileInput');
    const epsilon = parseFloat(document.getElementById('epsilon').value);
    const numColors = parseInt(document.getElementById('numColors').value, 10);
    const minArea = parseInt(document.getElementById('minArea').value, 10);
    const maxRes = parseInt(document.getElementById('maxRes').value, 10);

    if (!fileInput.files[0]) {
        alert('Select or drop an image first');
        return;
    }

    const file = fileInput.files[0];
    const reader = new FileReader();
    const startedAt = performance.now();

    startProgressSimulation();

    reader.onload = async function(event) {
        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: event.target.result,
                    epsilon,
                    num_colors: numColors,
                    min_area: minArea,
                    max_resolution: maxRes,
                }),
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error);
            }

            finishProgress();

            const stats = result.data.stats;
            lastDesmosStrings = Array.isArray(result.data.desmos_strings) ? result.data.desmos_strings : [];
            lastDesmosExpressions = Array.isArray(result.data.desmos_expressions) ? result.data.desmos_expressions : [];
            lastDesmosScript = buildCopyScript(lastDesmosExpressions);

            document.getElementById('downloadBtn').disabled = lastDesmosStrings.length === 0;
            document.getElementById('copyScriptBtn').disabled = lastDesmosExpressions.length === 0;

            eval(result.data.desmos_script);
            calculator.resize();

            const generationTime = performance.now() - startedAt;
            updateFooterMetrics(stats, generationTime, lastDesmosStrings, lastDesmosExpressions);
        } catch (error) {
            stopProgressSimulation();
            updateProgress('Failed', 100, error.message);
        }
    };

    reader.readAsDataURL(file);
}

function startProgressSimulation() {
    stopProgressSimulation();
    let stageIndex = 0;
    updateProgress(STAGES[0].name, STAGES[0].percent, STAGES[0].detail);
    progressTimer = setInterval(() => {
        stageIndex = Math.min(stageIndex + 1, STAGES.length - 1);
        const stage = STAGES[stageIndex];
        updateProgress(stage.name, stage.percent, stage.detail);
        if (stageIndex === STAGES.length - 1) {
            clearInterval(progressTimer);
            progressTimer = null;
        }
    }, 650);
}

function finishProgress() {
    stopProgressSimulation();
    updateProgress('Render Complete', 100, 'Equations loaded into the Desmos workspace.');
}

function stopProgressSimulation() {
    if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
    }
}

function updateProgress(name, percent, detail) {
    document.getElementById('stageName').textContent = name;
    document.getElementById('stagePercent').textContent = `${percent}%`;
    document.getElementById('stageDetail').textContent = detail;
    document.getElementById('progressFill').style.width = `${percent}%`;
}

function updateFooterMetrics(stats, generationTime, desmosStrings, expressions) {
    const estimatedBytes = desmosStrings.join('\n').length + JSON.stringify(expressions).length;
    document.getElementById('metricPolygons').textContent = stats.total_polygons.toLocaleString();
    document.getElementById('metricTime').textContent = `${Math.round(generationTime)} ms`;
    document.getElementById('metricPalette').textContent = `${stats.unique_colors} / ${stats.requested_colors}`;
    document.getElementById('metricMemory').textContent = formatMemoryPressure(estimatedBytes);
}

function formatMemoryPressure(bytes) {
    if (bytes < 2_000_000) {
        return `Low :: ${formatBytes(bytes)}`;
    }
    if (bytes < 8_000_000) {
        return `Moderate :: ${formatBytes(bytes)}`;
    }
    return `High :: ${formatBytes(bytes)}`;
}

function formatBytes(bytes) {
    if (!bytes) {
        return '0 B';
    }
    const units = ['B', 'KB', 'MB', 'GB'];
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / (1024 ** exponent);
    return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function buildCopyScript(expressions) {
    return `Calc.setExpressions(${JSON.stringify(expressions, null, 2)});`;
}

async function copyDesmosScript() {
    if (!lastDesmosScript) {
        alert('Generate polygons first');
        return;
    }

    await navigator.clipboard.writeText(lastDesmosScript);
    console.log(`Copied Desmos script with ${lastDesmosExpressions.length} expressions`);
    updateProgress('Script Copied', 100, 'Desmos script copied to the system clipboard.');
}

function downloadEquations() {
    if (!lastDesmosStrings.length) {
        alert('Generate polygons first');
        return;
    }

    const text = lastDesmosStrings.join('\n');
    console.log(`Exported ${lastDesmosStrings.length} polygon lines`);

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'desmos_art.txt';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}
