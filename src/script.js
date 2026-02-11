// 1. НАСТРОЙКИ И КОНСТАНТЫ
const WS_URL = 'ws://127.0.0.1:8765';
let socket;
let reconnectTimer;

const canvas = document.getElementById('ring-canvas');
const ctx = canvas.getContext('2d');

let themeConfig = {
    name: 'default',
    cpuColor: '#50b4ff',
    gpuColor: '#9b59ff'
};

// 2. ИНИЦИАЛИЗАЦИЯ СОКЕТА (Для музыки и тем)
function connect() {
    if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
    }

    socket = new WebSocket(WS_URL);

    socket.onopen = () => console.log(">>> КРАКЕН ПОДКЛЮЧЕН К СЕРВЕРУ");

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleServerData(data);
        } catch (e) {
            console.error("Ошибка парсинга данных:", e);
        }
    };

    socket.onclose = () => {
        reconnectTimer = setTimeout(connect, 2000);
    };

    socket.onerror = () => socket.close();
}

// 3. ФУНКЦИЯ РИСОВАНИЯ (Кольца)
function draw(cpu, gpu) {
    const x = 160, y = 160; 
    const radius = 138;     
    const width = 35;       
    
    ctx.clearRect(0, 0, 320, 320);

    const screen = document.querySelector('.screen');
    const isDark = screen.classList.contains('dark-mode') || screen.classList.contains('theme-minimal');
    
    // Фоновое кольцо
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'; 
    ctx.lineWidth = width;
    ctx.stroke();

    // CPU Дуга
    const cpuSpread = (Math.min(cpu, 100) / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI - cpuSpread, Math.PI + cpuSpread);
    ctx.strokeStyle = themeConfig.cpuColor; 
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();

    // GPU Дуга
    const gpuSpread = (Math.min(gpu, 100) / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, 0 - gpuSpread, 0 + gpuSpread);
    ctx.strokeStyle = themeConfig.gpuColor;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// 4. ТЕМЫ
function applyTheme(themeName) {
    const screen = document.querySelector('.screen');
    screen.className = 'screen'; // Сброс всех классов
    screen.classList.add(`theme-${themeName}`);
    themeConfig.name = themeName;

    const colors = {
        'cyberpunk': { cpu: '#fcee0a', gpu: '#00ff41' },
        'minimal':   { cpu: '#ffffff', gpu: '#888888' },
        'default':   { cpu: '#50b4ff', gpu: '#9b59ff' }
    };

    const selected = colors[themeName] || colors.default;
    themeConfig.cpuColor = selected.cpu;
    themeConfig.gpuColor = selected.gpu;
}

// 5. ОБРАБОТКА ДАННЫХ СЕРВЕРА (Музыка)
function handleServerData(data) {
    const screen = document.querySelector('.screen');
    const bgFull = document.getElementById('bg-cover-full');
    const pill = document.getElementById('music-pill');
    const pillCover = document.getElementById('pill-cover'); 
    const trackElem = document.getElementById('track-name');
    const artistElem = document.getElementById('artist-name');
    const trackContainer = document.querySelector('.track-container');
    const artistContainer = document.querySelector('.artist-container');

    if (data.theme && data.theme !== themeConfig.name) {
        applyTheme(data.theme);
    }

    if (data.music && data.music.title) {
        screen.classList.add('dark-mode');
        pill.classList.add('active');
        
        const currentService = data.music.service || 'other';
        pillCover.style.backgroundImage = `url('assets/${currentService}.png')`;

        if (trackElem.innerText !== data.music.title) {
            trackElem.innerText = data.music.title;
            artistElem.innerText = (data.music.artist || 'СИСТЕМА').toUpperCase();
            
            // Сброс и запуск бегущей строки
            [trackElem, artistElem].forEach(el => {
                el.classList.remove('animate-marquee');
                setTimeout(() => {
                    if (el.scrollWidth > el.parentElement.offsetWidth) {
                        el.classList.add('animate-marquee');
                    }
                }, 100);
            });
        }

        if (data.music.cover) {
            bgFull.style.backgroundImage = `url('data:image/jpeg;base64,${data.music.cover}')`;
            bgFull.classList.add('active');
        }
    } else {
        pill.classList.remove('active');
        bgFull.classList.remove('active');
    }
}

// 6. ОФИЦИАЛЬНАЯ ИНТЕГРАЦИЯ NZXT (Температуры)
window.nzxt = {
    v1: {
        onMonitoringDataUpdate: (data) => {
            if (!data.cpus || !data.gpus) return;

            const cpuTemp = Math.round(data.cpus[0].temperature);
            const gpuTemp = Math.round(data.gpus[0].temperature);

            document.getElementById('cpu-temp').innerText = cpuTemp;
            document.getElementById('gpu-temp').innerText = gpuTemp;

            // Рисуем кольца данными от NZXT
            draw(cpuTemp, gpuTemp);
        }
    }
};

// Запуск
connect();
