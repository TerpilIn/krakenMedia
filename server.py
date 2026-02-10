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
import shutil
import webview
from aiohttp import web
from threading import Thread
import time

# --- КОНФИГУРАЦИЯ ПУТЕЙ ---
APP_NAME = "KrakenIntegra"
APPDATA_PATH = os.path.join(os.environ['APPDATA'], APP_NAME)
EXE_NAME = "KrakenControl.exe"
FINAL_EXE_PATH = os.path.join(APPDATA_PATH, EXE_NAME)

# Твоя ссылка на GitHub Pages
CONFIG_URL = "https://terpilin.github.io/krakenMedia/config.html"

# --- СОСТОЯНИЕ ---
last_track_id, last_cover_b64, current_service = "", None, "other"
current_theme = "default"

# --- ЛОГИКА ИНСТАЛЛЯЦИИ ---
def install_and_setup():
    if not os.path.exists(APPDATA_PATH):
        os.makedirs(APPDATA_PATH)

    current_exe = sys.executable
    if os.path.abspath(current_exe) != os.path.abspath(FINAL_EXE_PATH):
        try:
            shutil.copy2(current_exe, FINAL_EXE_PATH)
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')

            # 1. Автозагрузка
            startup = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
            shortcut = shell.CreateShortCut(os.path.join(startup, f"{APP_NAME}_Service.lnk"))
            shortcut.Targetpath = FINAL_EXE_PATH
            shortcut.Arguments = "--service"
            shortcut.WindowStyle = 7 
            shortcut.save()

            # 2. Рабочий стол
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            control_link = shell.CreateShortCut(os.path.join(desktop, "Kraken Control Center.lnk"))
            control_link.Targetpath = FINAL_EXE_PATH
            control_link.Arguments = "--config"
            control_link.IconLocation = FINAL_EXE_PATH
            control_link.save()

            os.startfile(FINAL_EXE_PATH, arguments="--service")
            sys.exit()
        except Exception as e:
            print(f"Ошибка инсталляции: {e}")

# --- ФУНКЦИИ МЕДИА ---
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
        
        if "spotify" in source_app: current_service = "spotify"
        elif any(x in source_app for x in ["yandex", "45347"]): current_service = "yandex"
        else: current_service = "other"
        
        track_id = f"{props.title}_{props.artist}"
        if track_id != last_track_id:
            last_track_id = track_id
            last_cover_b64 = await get_thumbnail_base64(props.thumbnail)
            
        return {"title": props.title, "artist": props.artist, "service": current_service, "cover": last_cover_b64}
    except: return None

# --- СЕРВЕРНАЯ ЛОГИКА ---
async def ws_handler(websocket):
    while True:
        try:
            payload = {
                "cpu_temp": int(psutil.cpu_percent()), 
                "gpu_temp": int(psutil.virtual_memory().percent), # Пример, можно заменить на GPU
                "music": await _get_media_data(),
                "theme": current_theme 
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(1)
        except: break

async def change_theme(request):
    global current_theme
    current_theme = request.match_info.get('name', "default")
    print(f">>> Тема изменена на: {current_theme}")
    # Важно: CORS заголовки, чтобы GitHub Pages мог достучаться до локалки
    return web.Response(text="OK", headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    })

def start_servers():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    ws_server = websockets.serve(ws_handler, "127.0.0.1", 8765)
    app = web.Application()
    app.add_routes([web.get('/set_theme/{name}', change_theme)])
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    
    loop.run_until_complete(asyncio.gather(ws_server, site.start()))
    loop.run_forever()

if __name__ == "__main__":
    # 1. Установка
    install_and_setup()

    # 2. Определение режима
    is_service = "--service" in sys.argv
    is_config = "--config" in sys.argv

    # 3. Запуск серверов в фоне
    Thread(target=start_servers, daemon=True).start()

    if is_config:
        # Открываем окно управления
        webview.create_window('Kraken Control Center', CONFIG_URL, width=940, height=620, resizable=False)
        webview.start()
    else:
        # Режим службы (висим в процессах)
        while True: time.sleep(100)
