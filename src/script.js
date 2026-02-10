const socket = new WebSocket('ws://127.0.0.1:8765');
const canvas = document.getElementById('ring-canvas');
const ctx = canvas.getContext('2d');
let themeConfig = { name: 'default', cpu: '#50b4ff', gpu: '#9b59ff' };

socket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    document.getElementById('cpu-temp').innerText = data.cpu_temp;
    document.getElementById('gpu-temp').innerText = data.gpu_temp;
    
    if (data.theme && data.theme !== themeConfig.name) {
        themeConfig.name = data.theme;
        if(data.theme === 'cyberpunk') { themeConfig.cpu = '#fcee0a'; themeConfig.gpu = '#00ff41'; }
        else if(data.theme === 'minimal') { themeConfig.cpu = '#ffffff'; themeConfig.gpu = '#444444'; }
        else { themeConfig.cpu = '#50b4ff'; themeConfig.gpu = '#9b59ff'; }
    }
    
    drawRings(data.cpu_temp, data.gpu_temp);
    updateMedia(data.music);
};

function drawRings(cpu, gpu) {
    const x = 160, y = 160, r = 138, w = 35; // Координаты для 320px
    ctx.clearRect(0, 0, 320, 320);
    
    // Фон
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'; ctx.lineWidth = w; ctx.stroke();

    const arc = (val, color, start) => {
        const spread = (val / 100) * (0.35 * Math.PI);
        ctx.beginPath(); ctx.arc(x, y, r, start - spread, start + spread);
        ctx.strokeStyle = color; ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.stroke();
    };
    arc(cpu, themeConfig.cpu, Math.PI);
    arc(gpu, themeConfig.gpu, 0);
}

function updateMedia(m) {
    const pill = document.getElementById('music-pill');
    if (m && m.title) {
        pill.classList.add('active');
        document.getElementById('track-name').innerText = m.title;
        document.getElementById('artist-name').innerText = (m.artist || 'СИСТЕМА').toUpperCase();
        if (m.cover) document.getElementById('bg-cover-full').style.backgroundImage = `url('data:image/jpeg;base64,${m.cover}')`;
    } else { pill.classList.remove('active'); }
}
