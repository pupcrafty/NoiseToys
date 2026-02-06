// Connect to Socket.IO server
const socket = io();

// DOM elements
const connectionStatus = document.getElementById('connection-status');
const thresholdSlider = document.getElementById('normalized-threshold-slider');
const thresholdValueLabel = document.getElementById('normalized-threshold-value');

// Audio playback controls
const playbackToggle = document.getElementById('playback-toggle');
const volumeSlider = document.getElementById('volume-slider');
const volumeValue = document.getElementById('volume-value');

// Web Audio API setup for browser playback
let audioContext = null;
let audioBufferQueue = [];
let isPlaying = false;
let currentVolume = 1.0;
let sourceNode = null;
let gainNode = null;
let nextPlayTime = 0;
let sampleRate = 44100;

// Initialize Web Audio API
function initAudioContext() {
    if (!audioContext) {
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            gainNode = audioContext.createGain();
            gainNode.connect(audioContext.destination);
            gainNode.gain.value = currentVolume;
            console.log('Web Audio API initialized');
        } catch (e) {
            console.error('Failed to initialize Web Audio API:', e);
        }
    }
}

// Play audio samples using Web Audio API
function playAudioSamples(samples, samplerate) {
    if (!audioContext || audioContext.state === 'closed') {
        initAudioContext();
    }
    
    if (!audioContext || audioContext.state === 'suspended') {
        audioContext.resume();
    }
    
    if (!audioContext || !gainNode) {
        return;
    }
    
    try {
        // Update sample rate if changed
        if (samplerate && samplerate !== sampleRate) {
            sampleRate = samplerate;
        }
        
        // Create audio buffer
        const buffer = audioContext.createBuffer(1, samples.length, sampleRate);
        const channelData = buffer.getChannelData(0);
        
        // Copy samples to buffer
        for (let i = 0; i < samples.length; i++) {
            channelData[i] = samples[i];
        }
        
        // Schedule playback
        const currentTime = audioContext.currentTime;
        const playTime = Math.max(currentTime, nextPlayTime);
        
        const source = audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(gainNode);
        source.start(playTime);
        
        // Update next play time
        const duration = buffer.duration;
        nextPlayTime = playTime + duration;
        
    } catch (e) {
        console.error('Error playing audio samples:', e);
    }
}

// Threshold for normalized energy required to activate per-band pulse lights
let normalizedThreshold = 1.15;

if (thresholdSlider && thresholdValueLabel) {
    // Initialize from slider default
    normalizedThreshold = parseFloat(thresholdSlider.value) || 1.15;
    thresholdValueLabel.textContent = normalizedThreshold.toFixed(2);

    thresholdSlider.addEventListener('input', () => {
        const v = parseFloat(thresholdSlider.value);
        if (!Number.isNaN(v)) {
            normalizedThreshold = Math.min(Math.max(v, 0), 2);
            thresholdValueLabel.textContent = normalizedThreshold.toFixed(2);
        }
    });
}
// Analyzer band elements (11-band visualizer), using EMA channels from audio service
// Order here must match the detailed band order in the audio service so that
// band index values (0..10) line up across systems.
const analyzerBands = [
    {
        key: 'band_ema_sub_1',
        bar: document.getElementById('band-sub-1'),
        valueEl: document.getElementById('band-sub-1-value'),
        presenceEl: document.getElementById('presence-sub-1'),
        presenceKey: 'band_presence_sub_1',
        normEl: document.getElementById('normalized-sub-1'),
        normKey: 'band_normalized_sub_1',
    },
    {
        key: 'band_ema_sub_2',
        bar: document.getElementById('band-sub-2'),
        valueEl: document.getElementById('band-sub-2-value'),
        presenceEl: document.getElementById('presence-sub-2'),
        presenceKey: 'band_presence_sub_2',
        normEl: document.getElementById('normalized-sub-2'),
        normKey: 'band_normalized_sub_2',
    },
    {
        key: 'band_ema_bass_1',
        bar: document.getElementById('band-bass-1'),
        valueEl: document.getElementById('band-bass-1-value'),
        presenceEl: document.getElementById('presence-bass-1'),
        presenceKey: 'band_presence_bass_1',
        normEl: document.getElementById('normalized-bass-1'),
        normKey: 'band_normalized_bass_1',
    },
    {
        key: 'band_ema_bass_2',
        bar: document.getElementById('band-bass-2'),
        valueEl: document.getElementById('band-bass-2-value'),
        presenceEl: document.getElementById('presence-bass-2'),
        presenceKey: 'band_presence_bass_2',
        normEl: document.getElementById('normalized-bass-2'),
        normKey: 'band_normalized_bass_2',
    },
    {
        key: 'band_ema_low_mid_1',
        bar: document.getElementById('band-low-mid-1'),
        valueEl: document.getElementById('band-low-mid-1-value'),
        presenceEl: document.getElementById('presence-low-mid-1'),
        presenceKey: 'band_presence_low_mid_1',
        normEl: document.getElementById('normalized-low-mid-1'),
        normKey: 'band_normalized_low_mid_1',
    },
    {
        key: 'band_ema_low_mid_2',
        bar: document.getElementById('band-low-mid-2'),
        valueEl: document.getElementById('band-low-mid-2-value'),
        presenceEl: document.getElementById('presence-low-mid-2'),
        presenceKey: 'band_presence_low_mid_2',
        normEl: document.getElementById('normalized-low-mid-2'),
        normKey: 'band_normalized_low_mid_2',
    },
    {
        key: 'band_ema_mid_1',
        bar: document.getElementById('band-mid-1'),
        valueEl: document.getElementById('band-mid-1-value'),
        presenceEl: document.getElementById('presence-mid-1'),
        presenceKey: 'band_presence_mid_1',
        normEl: document.getElementById('normalized-mid-1'),
        normKey: 'band_normalized_mid_1',
    },
    {
        key: 'band_ema_mid_2',
        bar: document.getElementById('band-mid-2'),
        valueEl: document.getElementById('band-mid-2-value'),
        presenceEl: document.getElementById('presence-mid-2'),
        presenceKey: 'band_presence_mid_2',
        normEl: document.getElementById('normalized-mid-2'),
        normKey: 'band_normalized_mid_2',
    },
    {
        key: 'band_ema_high_1',
        bar: document.getElementById('band-high-1'),
        valueEl: document.getElementById('band-high-1-value'),
        presenceEl: document.getElementById('presence-high-1'),
        presenceKey: 'band_presence_high_1',
        normEl: document.getElementById('normalized-high-1'),
        normKey: 'band_normalized_high_1',
    },
    {
        key: 'band_ema_high_2',
        bar: document.getElementById('band-high-2'),
        valueEl: document.getElementById('band-high-2-value'),
        presenceEl: document.getElementById('presence-high-2'),
        presenceKey: 'band_presence_high_2',
        normEl: document.getElementById('normalized-high-2'),
        normKey: 'band_normalized_high_2',
    },
    {
        key: 'band_ema_air_1',
        bar: document.getElementById('band-air-1'),
        valueEl: document.getElementById('band-air-1-value'),
        presenceEl: document.getElementById('presence-air-1'),
        presenceKey: 'band_presence_air_1',
        normEl: document.getElementById('normalized-air-1'),
        normKey: 'band_normalized_air_1',
    },
];

// Attach a movable baseline line to each analyzer band bar
analyzerBands.forEach((band) => {
    if (!band.bar) return;
    // Append baseline directly to the band-bar (which has position: relative)
    const baselineEl = document.createElement('div');
    baselineEl.className = 'band-baseline';
    band.bar.appendChild(baselineEl);

    // Also create a numeric readout of the baseline under the bar
    // Insert it right after the band-bar element
    const baselineValueEl = document.createElement('span');
    baselineValueEl.className = 'band-baseline-value';
    baselineValueEl.textContent = '—';
    band.bar.insertAdjacentElement('afterend', baselineValueEl);
    band.baselineValueEl = baselineValueEl;

    // Store baseline DOM element and corresponding key on the band object
    band.baselineEl = baselineEl;
    band.baselineKey = band.key.replace('band_ema_', 'band_baseline_');

    // Threshold line for normalized energy (yellow)
    const thresholdEl = document.createElement('div');
    thresholdEl.className = 'threshold-line';
    band.bar.appendChild(thresholdEl);
    band.thresholdEl = thresholdEl;
});

// Helper to position all threshold lines based on current slider value
function applyThresholdToBands() {
    const thresholdPct = Math.min(Math.max(normalizedThreshold * 50, 0), 100);
    analyzerBands.forEach((band) => {
        if (band.thresholdEl) {
            band.thresholdEl.style.bottom = `${thresholdPct}%`;
        }
    });
}

// Initial placement
applyThresholdToBands();

// Update positions whenever the slider changes
if (thresholdSlider) {
    thresholdSlider.addEventListener('input', applyThresholdToBands);
}
const beatCircle = document.getElementById('beat-circle');

// Text readouts for winner stats
const rawWinnersText = document.getElementById('raw-winners-text');
const normWinnersText = document.getElementById('norm-winners-text');
const overallNormText = document.getElementById('overall-norm-text');
const bpmValue = document.getElementById('bpm-value');
const confValue = document.getElementById('conf-value');
const beatIdValue = document.getElementById('beat-id-value');

// Normalization values for visualization (adjust based on your data range)
const MAX_BAND_VALUE = 2.0; // Per-band scaling ceiling

// Human-friendly names for band indices (0..10), aligned with analyzerBands order
const BAND_INDEX_NAMES = [
    'Sub-1',
    'Sub-2',
    'Bass-1',
    'Bass-2',
    'Low-mid-1',
    'Low-mid-2',
    'Mid-1',
    'Mid-2',
    'High-1',
    'High-2',
    'Air-1',
];

// Pulse frequency readouts (0–4 over last 4 beats) per band
const pulse4Elems = {
    sub_1: document.getElementById('pulse4-sub-1'),
    sub_2: document.getElementById('pulse4-sub-2'),
    bass_1: document.getElementById('pulse4-bass-1'),
    bass_2: document.getElementById('pulse4-bass-2'),
    low_mid_1: document.getElementById('pulse4-low-mid-1'),
    low_mid_2: document.getElementById('pulse4-low-mid-2'),
    mid_1: document.getElementById('pulse4-mid-1'),
    mid_2: document.getElementById('pulse4-mid-2'),
    high_1: document.getElementById('pulse4-high-1'),
    high_2: document.getElementById('pulse4-high-2'),
    air_1: document.getElementById('pulse4-air-1'),
};

function computeOverallNormalizedEnergy(data) {
    // Take the max of all band_normalized_* values as a simple overall normalized metric
    const normKeys = [
        'band_normalized_sub_1',
        'band_normalized_sub_2',
        'band_normalized_bass_1',
        'band_normalized_bass_2',
        'band_normalized_low_mid_1',
        'band_normalized_low_mid_2',
        'band_normalized_mid_1',
        'band_normalized_mid_2',
        'band_normalized_high_1',
        'band_normalized_high_2',
        'band_normalized_air_1',
    ];
    let maxVal = 0.0;
    normKeys.forEach((k) => {
        const v = typeof data[k] === 'number' ? data[k] : 0.0;
        if (v > maxVal) maxVal = v;
    });
    return maxVal;
}

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
        const {
            key,
            bar,
            valueEl,
            baselineEl,
            baselineKey,
            baselineValueEl,
            presenceEl,
            presenceKey,
            normEl,
            normKey,
            thresholdEl,
        } = band;
        if (!bar || !valueEl) return;

        const raw = typeof data[key] === 'number' ? data[key] : 0.0;
        valueEl.textContent = raw.toFixed(2);

        // Per-band normalized pulse light: active when normalized value > 1.15
        let normalizedVal = 1.0;
        if (normKey && typeof data[normKey] === 'number') {
            normalizedVal = data[normKey];
        }

        if (normEl && normKey) {
            if (normalizedVal > normalizedThreshold) {
                normEl.classList.add('active');
            } else {
                normEl.classList.remove('active');
            }
        }

        // Update rolling baseline line (context-aware "normal" level)
        if (baselineEl && baselineKey) {
            const baseRaw = typeof data[baselineKey] === 'number' ? data[baselineKey] : null;
            if (baseRaw !== null && baseRaw > 1e-6) {
                // Baseline always at 50% height
                baselineEl.style.bottom = '50%';
                baselineEl.style.opacity = '1';

                // Scale bar height relative to baseline: baseline = 50%, so current = (raw/baseRaw) * 50%
                // Cap at 100% (when current is 2x baseline or more)
                const scaledPct = Math.min((raw / baseRaw) * 50, 100);
                bar.style.height = `${scaledPct}%`;

                if (baselineValueEl) {
                    baselineValueEl.textContent = baseRaw.toFixed(2);
                }
            } else {
                // Fallback to original scaling if no baseline yet
                const pct = Math.min((raw / MAX_BAND_VALUE) * 100, 100);
                bar.style.height = `${pct}%`;
                baselineEl.style.opacity = '0';
                if (baselineValueEl) {
                    baselineValueEl.textContent = '—';
                }
            }
        } else {
            // Fallback if no baseline element
            const pct = Math.min((raw / MAX_BAND_VALUE) * 100, 100);
            bar.style.height = `${pct}%`;
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

    // Update on-screen text values for winners and overall normalized energy
    const overallNorm = computeOverallNormalizedEnergy(data);
    if (rawWinnersText) {
        const r30 = typeof data.beat_raw_band_win_30 === 'number' ? data.beat_raw_band_win_30 : null;
        const r60 = typeof data.beat_raw_band_win_60 === 'number' ? data.beat_raw_band_win_60 : null;
        const r90 = typeof data.beat_raw_band_win_90 === 'number' ? data.beat_raw_band_win_90 : null;
        const fmt = (idx) =>
            idx === null || Number.isNaN(idx) || idx < 0 || idx >= BAND_INDEX_NAMES.length
                ? '–'
                : `${idx} (${BAND_INDEX_NAMES[idx]})`;
        rawWinnersText.textContent = `${fmt(r30)} / ${fmt(r60)} / ${fmt(r90)}`;
    }

    if (normWinnersText) {
        const n30 = typeof data.beat_norm_band_win_30 === 'number' ? data.beat_norm_band_win_30 : null;
        const n60 = typeof data.beat_norm_band_win_60 === 'number' ? data.beat_norm_band_win_60 : null;
        const n90 = typeof data.beat_norm_band_win_90 === 'number' ? data.beat_norm_band_win_90 : null;
        const fmt = (idx) =>
            idx === null || Number.isNaN(idx) || idx < 0 || idx >= BAND_INDEX_NAMES.length
                ? '–'
                : `${idx} (${BAND_INDEX_NAMES[idx]})`;
        normWinnersText.textContent = `${fmt(n30)} / ${fmt(n60)} / ${fmt(n90)}`;
    }

    if (overallNormText) {
        overallNormText.textContent = overallNorm.toFixed(2);
    }

    // Update per-band pulse frequency values for 4, 8, 16, 32 beats
    const pulseWindows = [4, 8, 16, 32];
    const bandKeys = ['sub-1', 'sub-2', 'bass-1', 'bass-2', 'low-mid-1', 'low-mid-2', 
                      'mid-1', 'mid-2', 'high-1', 'high-2', 'air-1'];
    
    pulseWindows.forEach(window => {
        bandKeys.forEach(bandKey => {
            const el = document.getElementById(`pulse${window}-${bandKey}`);
            if (!el) return;
            const oscKey = `band_pulse${window}_${bandKey.replace('-', '_')}`;
            const v = typeof data[oscKey] === 'number' ? data[oscKey] : 0;
            el.textContent = v.toString();
        });
    });
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

// Initialize audio context - browsers require user interaction
// Try to initialize on page load, but will resume on first user interaction
initAudioContext();

// Resume audio context on any user interaction (required by browsers)
document.addEventListener('click', () => {
    if (audioContext && audioContext.state === 'suspended') {
        audioContext.resume().then(() => {
            console.log('Audio context resumed');
        });
    }
}, { once: false });

// Audio Playback Controls
if (playbackToggle) {
    playbackToggle.addEventListener('change', (e) => {
        const enabled = e.target.checked;
        socket.emit('set_playback_enabled', enabled);
        
        // Initialize/resume audio context when enabling
        if (enabled && audioContext && audioContext.state === 'suspended') {
            audioContext.resume();
        }
    });
}

if (volumeSlider && volumeValue) {
    // Initialize volume display
    volumeValue.textContent = `${volumeSlider.value}%`;
    currentVolume = volumeSlider.value / 100.0;
    
    volumeSlider.addEventListener('input', (e) => {
        const volume = parseInt(e.target.value);
        volumeValue.textContent = `${volume}%`;
        currentVolume = volume / 100.0;
        
        // Update gain node
        if (gainNode) {
            gainNode.gain.value = currentVolume;
        }
        
        socket.emit('set_playback_volume', currentVolume);
    });
}

// Receive playback state updates from server
socket.on('playback_state', (data) => {
    if (playbackToggle && typeof data.enabled === 'boolean') {
        playbackToggle.checked = data.enabled;
    }
    if (volumeSlider && volumeValue && typeof data.volume === 'number') {
        const volumePercent = Math.round(data.volume * 100);
        volumeSlider.value = volumePercent;
        volumeValue.textContent = `${volumePercent}%`;
        currentVolume = data.volume;
        if (gainNode) {
            gainNode.gain.value = currentVolume;
        }
    }
});

// Receive audio samples from server and play them
socket.on('audio_samples', (data) => {
    if (playbackToggle && playbackToggle.checked && data.samples && data.samplerate) {
        playAudioSamples(data.samples, data.samplerate);
    }
});
