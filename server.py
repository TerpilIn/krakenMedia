import asyncio
import websockets
import json
import psutil 
import pygetwindow as gw
import winrt.windows.media.control as wmc
import winrt.windows.storage.streams as streams
import base64
import os
import sys
import webview # Для окна Web App
from aiohttp import web
from threading import Thread

# --- СОСТОЯНИЕ ---
last_track_id, last_cover_b64, current_service = "", None, "other"
current_theme = "default"

# --- ЛОГИКА СОЗДАНИЯ ЯРЛЫКА ---
def create_shortcut():
    try:
        from win32com.client import Dispatch
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        path = os.path.join(desktop, "Kraken Control.lnk")
        
        if not os.path.exists(path):
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(path)
            # Если запущено как EXE, берем путь к EXE, иначе к Python
            target = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            shortcut.Targetpath = os.path.abspath(target)
            shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(target))
            shortcut.IconLocation = os.path.abspath(target)
            shortcut.save()
            print(">>> Ярлык на рабочем столе создан")
    except Exception as e:
        print(f"Не удалось создать ярлык: {e}")

# --- ТВОИ ФУНКЦИИ (МЕДИА И WS) ---
async def get_thumbnail_base64(thumbnail_ref):
    if not thumbnail_ref: return None
    try:
        stream = await thumbnail_ref.open_read_async()
        reader = streams.DataReader(stream.get_input_stream_at(0))
        await reader.load_async(stream.size)
        buffer = bytearray(stream.size)
        reader.read_bytes(buffer)
        return base64.b64encode(buffer).decode('utf-8')
    except: return None

async def _get_media_data():
    global last_track_id, last_cover_b64, current_service
    try:
        manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        sessions = manager.get_sessions()
        if not sessions: return None
        active_session = next((s for s in sessions if s.get_playback_info().playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING), None)
        if not active_session: active_session = manager.get_current_session() or sessions[0]
        source_app = active_session.source_app_user_model_id.lower()
        props = await active_session.try_get_media_properties_async()
        if not props or not props.title: return None
        
        # Определение сервиса... (твой код без изменений)
        if "spotify" in source_app: current_service = "spotify"
        elif any(x in source_app for x in ["yandex", "45347"]): current_service = "yandex"
        elif any(br in source_app for br in ["chrome", "edge", "browser"]):
            titles = str(gw.getAllTitles()).lower()
            if any(x in titles for x in ["яндекс музыка", "yandex music"]): current_service = "yandex"
            elif "youtube" in titles: current_service = "youtube"
            elif "spotify" in titles: current_service = "spotify"

        track_id = f"{props.title}_{props.artist}"
        if track_id != last_track_id:
            last_track_id = track_id
            last_cover_b64 = await get_thumbnail_base64(props.thumbnail)
        return {"title": props.title, "artist": props.artist, "service": current_service, "cover": last_cover_b64}
    except: return None

async def ws_handler(websocket):
    while True:
        try:
            payload = {
                "cpu_temp": int(35 + (psutil.cpu_percent() * 0.4)), 
                "gpu_temp": int(40 + (psutil.virtual_memory().percent * 0.3)), 
                "music": await _get_media_data(),
                "theme": current_theme 
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(1)
        except: break

async def change_theme(request):
    global current_theme
    current_theme = request.match_info.get('name', "default")
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# --- ЗАПУСК ФОНОВОГО СЕРВЕРА ---
def start_servers():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    ws_server = websockets.serve(ws_handler, "127.0.0.1", 8765)
    app = web.Application()
    app.add_routes([web.get('/set_theme/{name}', change_theme)])
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    http_site = web.TCPSite(runner, '127.0.0.1', 8080)
    
    loop.run_until_complete(asyncio.gather(ws_server, http_site.start()))
    loop.run_forever()

if __name__ == "__main__":
    # 1. Ярлык
    create_shortcut()

    # 2. Сервер в отдельном потоке (чтобы не блокировать окно)
    t = Thread(target=start_servers, daemon=True)
    t.start()

    # 3. Окно Web App
    # Если ты упакуешь в EXE, путь к файлу нужно брать через _MEIPASS
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_path, 'config.html')

    window = webview.create_window(
        'Kraken Control Center', 
        config_path, 
        width=940, 
        height=620, 
        resizable=False,
        background_color='#0a0a0a'
    )
    webview.start()
