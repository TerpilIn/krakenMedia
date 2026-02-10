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
        console.log(">>> Связь потеряна. Попытка переподключения...");
        reconnectTimer = setTimeout(connect, 2000); // Пробуем снова через 2 сек
    };

    socket.onerror = (err) => {
        console.error("Ошибка сокета. Возможно, EXE не запущен.");
        socket.close();
    };
}

// Рендеринг графики
function draw(cpu, gpu) {
    const x = 240, y = 240, radius = 210, width = 50;
    ctx.clearRect(0, 0, 480, 480);

    const isDark = document.querySelector('.screen').classList.contains('dark-mode');
    
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

// Смена тем (CSS + Цвета Canvas)
function applyTheme(themeName) {
    const screen = document.querySelector('.screen');
    
    // Чистим старые классы тем
    const themes = ['theme-default', 'theme-cyberpunk', 'theme-minimal'];
    themes.forEach(t => screen.classList.remove(t));
    
    screen.classList.add(`theme-${themeName}`);
    themeConfig.name = themeName;

    // Пресеты цветов для рисования
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

    // 1. Тема
    if (data.theme && data.theme !== themeConfig.name) {
        applyTheme(data.theme);
    }

    // 2. Датчики
    const cpu = data.cpu_temp || 0;
    const gpu = data.gpu_temp || 0;
    document.getElementById('cpu-temp').innerText = cpu;
    document.getElementById('gpu-temp').innerText = gpu;
    draw(cpu, gpu);

    // 3. Музыка
    if (data.music && data.music.title) {
        screen.classList.add('dark-mode');
        pill.classList.add('active');
        
        const service = data.music.service || 'other';
        pillCover.style.backgroundImage = `url('assets/${service}.png')`;

        if (trackElem.innerText !== data.music.title) {
            trackElem.innerText = data.music.title;
            artistElem.innerText = (data.music.artist || 'СИСТЕМА').toUpperCase();
            
            // Перезапуск анимации бегущей строки
            trackElem.classList.remove('animate-marquee');
            void trackElem.offsetWidth; // Магия для сброса анимации
            if (trackElem.scrollWidth > trackContainer.offsetWidth) {
                trackElem.classList.add('animate-marquee');
            }
        }

        if (data.music.cover) {
            bgFull.style.backgroundImage = `url('data:image/jpeg;base64,${data.music.cover}')`;
            bgFull.classList.add('active');
        } else {
            bgFull.classList.remove('active');
        }
    } else {
        screen.classList.remove('dark-mode');
        pill.classList.remove('active');
        bgFull.classList.remove('active');
        trackElem.innerText = "";
    }
}

// Запуск
connect();
