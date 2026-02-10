const WS_URL = 'ws://127.0.0.1:8765';
let socket;
let reconnectTimer;

const canvas = document.getElementById('ring-canvas');
const ctx = canvas.getContext('2d');

// Конфиг темы (цвета подбираются под 320px)
let themeConfig = {
    name: 'default',
    cpuColor: '#00d1ff', // Тот самый яркий синий
    gpuColor: '#9d00ff'  // Тот самый фиолетовый
};

function connect() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("Connected to Kraken Server");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateUI(data);
    };

    socket.onclose = () => {
        reconnectTimer = setTimeout(connect, 2000);
    };
}

// Рендеринг колец (Центровка 160/160 для экрана 320)
function drawRings(cpu, gpu) {
    const x = 160;
    const y = 160;
    const radius = 135;
    const lineWidth = 30;

    ctx.clearRect(0, 0, 320, 320);

    // Фоновое полупрозрачное кольцо
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = lineWidth;
    ctx.stroke();

    // CPU (Левая дуга)
    const cpuAngle = (cpu / 100) * (0.4 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI - cpuAngle, Math.PI + cpuAngle);
    ctx.strokeStyle = themeConfig.cpuColor;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // GPU (Правая дуга)
    const gpuAngle = (gpu / 100) * (0.4 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, 0 - gpuAngle, 0 + gpuAngle);
    ctx.strokeStyle = themeConfig.gpuColor;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();
}

function updateUI(data) {
    // Температуры
    document.getElementById('cpu-temp').innerText = data.cpu_temp;
    document.getElementById('gpu-temp').innerText = data.gpu_temp;
    drawRings(data.cpu_temp, data.gpu_temp);

    const pill = document.getElementById('music-pill');
    const track = document.getElementById('track-name');
    const artist = document.getElementById('artist-name');
    const pillCover = document.getElementById('pill-cover');
    const bgFull = document.getElementById('bg-cover-full');
    const container = document.querySelector('.track-container');

    if (data.music && data.music.title) {
        pill.classList.add('active');
        
        // Логика иконки сервиса (из папки assets)
        const service = data.music.service || 'other';
        pillCover.style.backgroundImage = `url('assets/${service}.png')`;

        // Бегущая строка
        if (track.innerText !== data.music.title) {
            track.innerText = data.music.title;
            artist.innerText = (data.music.artist || "СИСТЕМА").toUpperCase();

            track.classList.remove('animate-marquee');
            if (track.scrollWidth > container.offsetWidth) {
                track.classList.add('animate-marquee');
            }
        }

        // Фоновая обложка трека
        if (data.music.cover) {
            bgFull.style.backgroundImage = `url('data:image/jpeg;base64,${data.music.cover}')`;
        }
    } else {
        pill.classList.remove('active');
        track.innerText = "Ожидание...";
        artist.innerText = "СИСТЕМА";
        pillCover.style.backgroundImage = `url('assets/other.png')`;
        bgFull.style.backgroundImage = "none";
    }
}

connect();
