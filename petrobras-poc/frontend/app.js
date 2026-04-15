const API_BASE = "http://127.0.0.1:8000";
let wallet = null;

// Gamification State
let currentState = {
    ip: "10.0.1.45", // Default Corporate
    gps_variance: 0.0,
    hour: 12,
    iso_time: new Date().toISOString()
};

// Elements
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const btnSend = document.getElementById('btn-send');
const deviceAddressSpan = document.getElementById('device-address');
const statusDot = document.getElementById('status-dot');

// ==== 1. MAP & GEOFENCING (Leaflet.js) ====
// We use coordinates nearby a realistic center (e.g. Petrobras CENPES -22.859, -43.230)
const CENPES_COORDS = [-22.859, -43.230]; 
const map = L.map('map', { dragging: true, scrollWheelZoom: false }).setView(CENPES_COORDS, 14);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; CartoDB'
}).addTo(map);

// Geofence Circle (e.g. 500m radius safe zone) utilizing Petrobras Green
const geofence = L.circle(CENPES_COORDS, {
    color: '#008a3e', fillColor: '#008a3e', fillOpacity: 0.15, radius: 500
}).addTo(map);

// Draggable Marker representing the user's Smart Glasses (Petrobras Yellow)
const marker = L.marker(CENPES_COORDS, {
    draggable: true,
    icon: L.divIcon({ className: 'custom-pin', html: '<div style="width:14px;height:14px;background:#ffcd00;border-radius:50%;box-shadow:0 0 10px #ffcd00;"></div>' })
}).addTo(map);

marker.on('drag', function(e) {
    const latlng = marker.getLatLng();
    const distance = map.distance(CENPES_COORDS, latlng); // in meters
    
    // Scale distance for the Sentinel AI model (1000m outward = ~2.0 variance)
    const variance = (distance / 500).toFixed(2);
    document.getElementById('gps-val').innerText = `${distance.toFixed(0)}m (Alerta: ${variance})`;
    currentState.gps_variance = parseFloat(variance);

    if (variance > 1.5) {
        geofence.setStyle({color: '#ef4444', fillColor: '#ef4444'});
        document.getElementById('gps-val').style.color = '#ef4444';
    } else {
        geofence.setStyle({color: '#008a3e', fillColor: '#008a3e'});
        document.getElementById('gps-val').style.color = 'var(--petro-yellow)';
    }
});

// ==== 2. TIMESTAMPS & CLOCK ====
const clockFace = document.querySelector('.clock');
const hourHand = document.getElementById('hour-hand');
const timeVal = document.getElementById('time-val');

function updateClockHands(deg) {
    let hour24 = Math.floor(deg / 15);
    if(hour24 < 0) hour24 = 0;
    if(hour24 > 23) hour24 = 23;

    currentState.hour = hour24;
    hourHand.style.transform = `rotate(${deg}deg)`;
    
    const formatted = hour24.toString().padStart(2, '0') + ':00';
    timeVal.innerText = formatted;
    
    // SOC Gamification: If night shift (Unusual hours), dim the whole screen ambient light
    if (hour24 >= 20 || hour24 <= 5) {
        document.body.style.backgroundColor = '#010306'; // Extra dark
        timeVal.style.color = '#f59e0b';
    } else {
        document.body.style.backgroundColor = 'var(--soc-bg)';
        timeVal.style.color = 'var(--petro-yellow)';
    }

    let d = new Date();
    d.setHours(hour24, 0, 0, 0);
    currentState.iso_time = d.toISOString();
}

// Initial position: 12:00 = 180 degrees
updateClockHands(180);

let isDraggingClock = false;
clockFace.addEventListener('mousedown', (e) => { isDraggingClock = true; calculateAngles(e); });
document.addEventListener('mouseup', () => { isDraggingClock = false; });
document.addEventListener('mousemove', (e) => { if(isDraggingClock) calculateAngles(e); });

function calculateAngles(e) {
    const rect = clockFace.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const x = e.clientX - cx;
    const y = e.clientY - cy;
    
    let rad = Math.atan2(y, x);
    let deg = rad * (180 / Math.PI) + 90; // offset 90deg so 0h is Top
    if (deg < 0) deg += 360;
    updateClockHands(deg);
}

// ==== 3. NETWORK SPOOFING TOGGLES ====
document.querySelectorAll('.net-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.net-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentState.ip = e.target.getAttribute('data-ip');
        addSystemLog(`Conexão roteada pelo IP de Origem: ${currentState.ip}`);
    });
});

// ==== 4. IDENTITY & CORE LOGIC ====
async function initializeIdentity() {
    let pk = localStorage.getItem('smart_glasses_pk');
    if (!pk) {
        wallet = ethers.Wallet.createRandom();
        localStorage.setItem('smart_glasses_pk', wallet.privateKey);
        try {
            await fetch(`${API_BASE}/api/admin/authorize?address=${wallet.address}`, { method: 'POST' });
            addSystemLog(`Hardware recém-fabricado. Device autorizado no Blockchain da Planta.`);
        } catch(e) {
            addSystemLog(`FALHA: Backend offline. O Blockchain não registrou as chaves localmente.`);
        }
    } else {
        wallet = new ethers.Wallet(pk);
        addSystemLog(`Autenticação Segura. Identity do Operador recuperada do HSM.`);
    }
    
    deviceAddressSpan.innerText = `${wallet.address.substring(0,8)}...${wallet.address.substring(36)}`;
    deviceAddressSpan.style.color = 'var(--petro-yellow)';
    statusDot.className = 'dot online';
    document.getElementById('identity-panel').classList.remove('glitch-panel');
}

function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerText = text;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}
function addSystemLog(text) { addMessage(`[SISTEMA]: ${text}`, 'system'); }

async function sendRequest() {
    const question = userInput.value.trim();
    if(!question) return;

    addMessage(question, 'user');
    userInput.value = '';

    const metadata = {
        ip: currentState.ip,
        timestamp: currentState.iso_time,
        gps_variance: currentState.gps_variance
    };

    const sortedMetadata = {};
    Object.keys(metadata).sort().forEach(k => sortedMetadata[k] = metadata[k]);
    const payloadString = JSON.stringify(sortedMetadata);
    
    addSystemLog('Criptografando payload com chave de dispositivo Zero Trust...');
    let signature;
    try {
        signature = await wallet.signMessage(payloadString);
    } catch(e) {
        addMessage(`ERRO CRÍTICO: Módulo de assinatura inoperante.`, 'error');
        return;
    }

    const payload = { message: question, metadata: sortedMetadata, signature: signature };

    try {
        const response = await fetch(`${API_BASE}/api/request`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            addMessage(`${data.response}`, 'bot');
        } else {
            addMessage(`ACESSO NEGADO (403)\nMotivo: ${data.detail}`, 'error');
        }
    } catch (err) {
        addMessage(`API DO GATEWAY INDISPONÍVEL. Todos os acessos externos bloqueados preventivamente.`, 'error');
    }
}

btnSend.addEventListener('click', sendRequest);
userInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendRequest(); });

// ==== 5. HACKING ANIMATION & SWITCH ====
const btnHack = document.getElementById('btn-gen-rogue-key');
btnHack.addEventListener('click', () => {
    btnHack.classList.add('is-glitching');
    document.getElementById('identity-panel').classList.add('glitch-panel');
    addSystemLog('ALERTA: Tentativa de sobreposição de hardware detectada...');
    
    setTimeout(() => {
        btnHack.classList.remove('is-glitching');
        wallet = ethers.Wallet.createRandom(); // Rogue identity
        deviceAddressSpan.innerText = `${wallet.address.substring(0,8)}... (CLONADO)`;
        deviceAddressSpan.style.color = '#ef4444';
        statusDot.className = 'dot offline';
        addSystemLog('AVISO CRÍTICO: Dispositivo físico clonado. Gateway não reconhecerá este aparelho no Inventário Central.');
    }, 1800);
});

document.getElementById('btn-restore-key').addEventListener('click', () => {
    initializeIdentity(); 
});

window.onload = initializeIdentity;
