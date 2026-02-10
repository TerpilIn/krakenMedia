// Настройки подключения
const WS_URL = 'ws://127.0.0.1:8765';
let socket;
let reconnectTimer;

const canvas = document.getElementById('ring-canvas');
const ctx = canvas.getContext('2d');

// Глобальный объект темы
let themeConfig = {
    name: 'default',
    cpuColor: '#50b4ff',
    gpuColor: '#9b59ff'
};

// Функция инициализации сокета с авто-реконнектом
function connect() {
    if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
    }

    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log(">>> КРАКЕН ПОДКЛЮЧЕН К СЕРВЕРУ");
        clearTimeout(reconnectTimer);
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleServerData(data);
        } catch (e) {
            console.error("Ошибка парсинга данных:", e);
        }
    };

    socket.onclose = () => {
        console.log(">>> Связь потеряна. Реконнект через 2с...");
        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(connect, 2000);
    };

    socket.onerror = () => {
        socket.close();
    };
}

// Рендеринг графики (Адаптировано под 320x320)
function draw(cpu, gpu) {
    const x = 160, y = 160; // Центр экрана 320/2
    const radius = 138;     // Подобрано под отступы 320px
    const width = 35;       // Линии стали чуть тоньше для изящности
    
    ctx.clearRect(0, 0, 320, 320);

    const screen = document.querySelector('.screen');
    const isDark = screen.classList.contains('dark-mode') || screen.classList.contains('theme-minimal');
    
    // Фоновое кольцо
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'; 
    ctx.lineWidth = width;
    ctx.stroke();

    // CPU Дуга (Слева)
    // Угол распространения 0.35 * PI (~63 градуса в каждую сторону от центра)
    const cpuSpread = (Math.min(cpu, 100) / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI - cpuSpread, Math.PI + cpuSpread);
    ctx.strokeStyle = themeConfig.cpuColor; 
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();

    // GPU Дуга (Справа)
    const gpuSpread = (Math.min(gpu, 100) / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, 0 - gpuSpread, 0 + gpuSpread);
    ctx.strokeStyle = themeConfig.gpuColor;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// Смена тем (CSS + Цвета Canvas)
function applyTheme(themeName) {
    const screen = document.querySelector('.screen');
    
    const classes = Array.from(screen.classList);
    classes.forEach(cls => {
        if (cls.startsWith('theme-')) screen.classList.remove(cls);
    });
    
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

// Основная логика обработки данных
function handleServerData(data) {
    const screen = document.querySelector('.screen');
    const bgFull = document.getElementById('bg-cover-full');
    const pill = document.getElementById('music-pill');
    const pillCover = document.getElementById('pill-cover'); 
    const trackElem = document.getElementById('track-name');
    const artistElem = document.getElementById('artist-name');
    const trackContainer = document.querySelector('.track-container');

    if (data.theme && data.theme !== themeConfig.name) {
        applyTheme(data.theme);
    }

    const cpu = data.cpu_temp || 0;
    const gpu = data.gpu_temp || 0;
    document.getElementById('cpu-temp').innerText = cpu;
    document.getElementById('gpu-temp').innerText = gpu;
    draw(cpu, gpu);

    if (data.music && data.music.title) {
        screen.classList.add('dark-mode');
        pill.classList.add('active');
        
        const service = data.music.service || 'other';
        pillCover.style.backgroundImage = `url('assets/${service}.png')`;

        if (trackElem.innerText !== data.music.title) {
            trackElem.innerText = data.music.title;
            artistElem.innerText = (data.music.artist || 'СИСТЕМА').toUpperCase();
            
            trackElem.classList.remove('animate-marquee');
            void trackElem.offsetWidth; 
            if (trackElem.scrollWidth > trackContainer.offsetWidth) {
                trackElem.classList.add('animate-marquee');
            }
        }

        if (data.music.cover) {
            bgFull.style.backgroundImage = `url('data:image/jpeg;base64,${data.music.cover}')`;
            bgFull.classList.add('active');
        } else {
            bgFull.classList.remove('active');
            bgFull.style.backgroundImage = "none";
        }
    } else {
        screen.classList.remove('dark-mode');
        pill.classList.remove('active');
        bgFull.classList.remove('active');
        bgFull.style.backgroundImage = "none";
        trackElem.classList.remove('animate-marquee');
        trackElem.innerText = "Ожидание...";
        artistElem.innerText = "СИСТЕМА";
    }
}

connect();
