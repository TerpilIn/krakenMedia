const socket = new WebSocket('ws://127.0.0.1:8765');
const canvas = document.getElementById('ring-canvas');
const ctx = canvas.getContext('2d');

// Глобальный объект для хранения текущих настроек темы
let themeConfig = {
    name: 'default',
    cpuColor: '#50b4ff',
    gpuColor: '#9b59ff'
};

function draw(cpu, gpu) {
    const x = 240, y = 240, radius = 210;
    const width = 50;
    
    ctx.clearRect(0, 0, 480, 480);

    const isDark = document.querySelector('.screen').classList.contains('dark-mode');
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)'; 
    ctx.lineWidth = width;
    ctx.stroke();

    // Используем цвета из конфига темы
    const cpuSpread = (cpu / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, Math.PI - cpuSpread, Math.PI + cpuSpread);
    ctx.strokeStyle = themeConfig.cpuColor; 
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();

    const gpuSpread = (gpu / 100) * (0.35 * Math.PI);
    ctx.beginPath();
    ctx.arc(x, y, radius, 0 - gpuSpread, 0 + gpuSpread);
    ctx.strokeStyle = themeConfig.gpuColor;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.stroke();
}

// Функция смены темы
function applyTheme(themeName) {
    const screen = document.querySelector('.screen');
    
    // Удаляем старые классы тем
    screen.classList.forEach(cls => {
        if (cls.startsWith('theme-')) screen.classList.remove(cls);
    });
    
    // Добавляем новый класс темы
    screen.classList.add(`theme-${themeName}`);
    themeConfig.name = themeName;

    // Логика предустановок цветов для тем
    if (themeName === 'cyberpunk') {
        themeConfig.cpuColor = '#fcee0a'; // Желтый
        themeConfig.gpuColor = '#00ff41'; // Зеленый матрица
    } else if (themeName === 'minimal') {
        themeConfig.cpuColor = '#ffffff';
        themeConfig.gpuColor = '#888888';
    } else {
        themeConfig.cpuColor = '#50b4ff';
        themeConfig.gpuColor = '#9b59ff';
    }
}

socket.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        const screen = document.querySelector('.screen');
        const bgFull = document.getElementById('bg-cover-full');
        const pill = document.getElementById('music-pill');
        const pillCover = document.getElementById('pill-cover'); 
        const trackElem = document.getElementById('track-name');
        const artistElem = document.getElementById('artist-name');
        const trackContainer = document.querySelector('.track-container');

        // ПРОВЕРКА СМЕНЫ ТЕМЫ
        if (data.theme && data.theme !== themeConfig.name) {
            applyTheme(data.theme);
        }

        // 1. Температуры
        if (data.cpu_temp !== undefined) document.getElementById('cpu-temp').innerText = data.cpu_temp;
        if (data.gpu_temp !== undefined) document.getElementById('gpu-temp').innerText = data.gpu_temp;
        draw(data.cpu_temp, data.gpu_temp);

        // 2. Логика музыкального плеера
        if (data.music && data.music.title) {
            screen.classList.add('dark-mode');
            pill.classList.add('active');
            
            const currentService = data.music.service || 'other';
            const serviceUrl = `url('assets/${currentService}.png')`;
            
            if (pillCover.style.backgroundImage !== serviceUrl) {
                pillCover.style.backgroundImage = serviceUrl;
                pillCover.style.backgroundSize = "65%";
                pillCover.style.backgroundRepeat = "no-repeat";
                pillCover.style.backgroundPosition = "center";
            }

            if (trackElem.innerText !== data.music.title) {
                trackElem.innerText = data.music.title;
                artistElem.innerText = (data.music.artist || 'СИСТЕМА').toUpperCase();
                
                trackElem.classList.remove('animate-marquee');
                setTimeout(() => {
                    if (trackElem.scrollWidth > trackContainer.offsetWidth) {
                        trackElem.classList.add('animate-marquee');
                    }
                }, 50);
            }

            if (data.music.cover) {
                const coverData = `url('data:image/jpeg;base64,${data.music.cover}')`;
                if (bgFull.style.backgroundImage !== coverData) {
                    bgFull.style.backgroundImage = coverData;
                    bgFull.classList.add('active');
                }
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
            trackElem.innerText = "";
        }
    } catch (e) {
        console.error("Ошибка JS:", e);
    }
};

socket.onopen = () => console.log(">>> КРАКЕН НА СВЯЗИ!");
