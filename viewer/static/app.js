// Connect to Socket.IO server
const socket = io();

// DOM elements
const connectionStatus = document.getElementById('connection-status');
// Analyzer band elements (11-band visualizer), using EMA channels from audio service
const analyzerBands = [
    { key: 'band_ema_sub_1', bar: document.getElementById('band-sub-1'), valueEl: document.getElementById('band-sub-1-value'), presenceEl: document.getElementById('presence-sub-1'), presenceKey: 'band_presence_sub_1' },
    { key: 'band_ema_sub_2', bar: document.getElementById('band-sub-2'), valueEl: document.getElementById('band-sub-2-value'), presenceEl: document.getElementById('presence-sub-2'), presenceKey: 'band_presence_sub_2' },
    { key: 'band_ema_bass_1', bar: document.getElementById('band-bass-1'), valueEl: document.getElementById('band-bass-1-value'), presenceEl: document.getElementById('presence-bass-1'), presenceKey: 'band_presence_bass_1' },
    { key: 'band_ema_bass_2', bar: document.getElementById('band-bass-2'), valueEl: document.getElementById('band-bass-2-value'), presenceEl: document.getElementById('presence-bass-2'), presenceKey: 'band_presence_bass_2' },
    { key: 'band_ema_low_mid_1', bar: document.getElementById('band-low-mid-1'), valueEl: document.getElementById('band-low-mid-1-value'), presenceEl: document.getElementById('presence-low-mid-1'), presenceKey: 'band_presence_low_mid_1' },
    { key: 'band_ema_low_mid_2', bar: document.getElementById('band-low-mid-2'), valueEl: document.getElementById('band-low-mid-2-value'), presenceEl: document.getElementById('presence-low-mid-2'), presenceKey: 'band_presence_low_mid_2' },
    { key: 'band_ema_mid_1', bar: document.getElementById('band-mid-1'), valueEl: document.getElementById('band-mid-1-value'), presenceEl: document.getElementById('presence-mid-1'), presenceKey: 'band_presence_mid_1' },
    { key: 'band_ema_mid_2', bar: document.getElementById('band-mid-2'), valueEl: document.getElementById('band-mid-2-value'), presenceEl: document.getElementById('presence-mid-2'), presenceKey: 'band_presence_mid_2' },
    { key: 'band_ema_high_1', bar: document.getElementById('band-high-1'), valueEl: document.getElementById('band-high-1-value'), presenceEl: document.getElementById('presence-high-1'), presenceKey: 'band_presence_high_1' },
    { key: 'band_ema_high_2', bar: document.getElementById('band-high-2'), valueEl: document.getElementById('band-high-2-value'), presenceEl: document.getElementById('presence-high-2'), presenceKey: 'band_presence_high_2' },
    { key: 'band_ema_air_1', bar: document.getElementById('band-air-1'), valueEl: document.getElementById('band-air-1-value'), presenceEl: document.getElementById('presence-air-1'), presenceKey: 'band_presence_air_1' },
];

// Attach a movable baseline line to each analyzer band bar
analyzerBands.forEach((band) => {
    if (!band.bar) return;
    // Append baseline directly to the band-bar (which has position: relative)
    const baselineEl = document.createElement('div');
    baselineEl.className = 'band-baseline';
    band.bar.appendChild(baselineEl);

    // Store baseline DOM element and corresponding key on the band object
    band.baselineEl = baselineEl;
    band.baselineKey = band.key.replace('band_ema_', 'band_baseline_');
});
const beatCircle = document.getElementById('beat-circle');
const bpmValue = document.getElementById('bpm-value');
const confValue = document.getElementById('conf-value');
const beatIdValue = document.getElementById('beat-id-value');

// Normalization values for visualization (adjust based on your data range)
const MAX_BAND_VALUE = 2.0; // Per-band scaling ceiling

// Connection status
socket.on('connect', () => {
    connectionStatus.textContent = 'Connected';
    connectionStatus.className = 'status-indicator connected';
});

socket.on('disconnect', () => {
    connectionStatus.textContent = 'Disconnected';
    connectionStatus.className = 'status-indicator disconnected';
});

// Audio data handler
socket.on('audio_data', (data) => {
    // Update analyzer bars for each detailed band
    analyzerBands.forEach((band) => {
        const { key, bar, valueEl, baselineEl, baselineKey, presenceEl, presenceKey } = band;
        if (!bar || !valueEl) return;

        const raw = typeof data[key] === 'number' ? data[key] : 0.0;
        const pct = Math.min((raw / MAX_BAND_VALUE) * 100, 100);
        bar.style.height = `${pct}%`;
        valueEl.textContent = raw.toFixed(2);

        // Update rolling baseline line (context-aware "normal" level)
        if (baselineEl && baselineKey) {
            const baseRaw = typeof data[baselineKey] === 'number' ? data[baselineKey] : null;
            if (baseRaw !== null) {
                const basePct = Math.min((baseRaw / MAX_BAND_VALUE) * 100, 100);
                baselineEl.style.bottom = `${basePct}%`;
                baselineEl.style.opacity = '1';
            } else {
                // Hide if we don't have a value yet
                baselineEl.style.opacity = '0';
            }
        }

        // Update presence indicator (hysteresis-based "this thing exists right now")
        if (presenceEl && presenceKey) {
            const isPresent = typeof data[presenceKey] === 'boolean' ? data[presenceKey] : false;
            if (isPresent) {
                presenceEl.classList.add('active');
            } else {
                presenceEl.classList.remove('active');
            }
        }
    });

    // Visual feedback for beat/pulse mapped onto low / high bands
    if (data.beat && analyzerBands[2] && analyzerBands[2].bar) { // Bass‑1
        const bassBar = analyzerBands[2].bar;
        bassBar.style.boxShadow = '0 0 20px rgba(255, 107, 107, 0.8)';
        setTimeout(() => {
            bassBar.style.boxShadow = '';
        }, 100);
    }

    if (data.pulse && analyzerBands[8] && analyzerBands[8].bar) { // High‑1
        const trebleBar = analyzerBands[8].bar;
        trebleBar.style.boxShadow = '0 0 20px rgba(69, 183, 209, 0.8)';
        setTimeout(() => {
            trebleBar.style.boxShadow = '';
        }, 100);
    }
});

// Beat data handler
socket.on('beat_data', (data) => {
    bpmValue.textContent = data.bpm.toFixed(1);
    confValue.textContent = data.confidence.toFixed(2);
    beatIdValue.textContent = data.beat_id;
});

// Beat event handler
socket.on('beat', (data) => {
    // Animate beat circle
    beatCircle.classList.add('beat');
    setTimeout(() => {
        beatCircle.classList.remove('beat');
    }, 150);
});

// Smooth animation for beat circle pulse
let beatPulseInterval = null;

socket.on('beat', () => {
    if (beatPulseInterval) {
        clearInterval(beatPulseInterval);
    }
    
    beatCircle.style.transition = 'all 0.15s ease-out';
    beatCircle.classList.add('beat');
    
    beatPulseInterval = setTimeout(() => {
        beatCircle.classList.remove('beat');
        beatCircle.style.transition = 'all 0.3s ease-out';
    }, 150);
});
