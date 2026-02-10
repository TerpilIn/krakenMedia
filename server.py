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

CONFIG_URL = "https://terpilin.github.io/krakenMedia/config.html"

# --- СОСТОЯНИЕ ---
last_track_id, last_cover_b64, current_service = "", None, "other"
current_theme = "default"

# --- ЛОГИКА ИНСТАЛЛЯЦИИ ---
def install_and_setup():
    if not os.path.exists(APPDATA_PATH):
        os.makedirs(APPDATA_PATH)

    current_exe = sys.executable
    # Если запущен не из AppData и не в режиме разработки (python.exe)
    if "python.exe" not in current_exe.lower() and os.path.abspath(current_exe) != os.path.abspath(FINAL_EXE_PATH):
        try:
            shutil.copy2(current_exe, FINAL_EXE_PATH)
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')

            startup = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
            s_link = shell.CreateShortCut(os.path.join(startup, f"{APP_NAME}_Service.lnk"))
            s_link.Targetpath = FINAL_EXE_PATH
            s_link.Arguments = "--service"
            s_link.WindowStyle = 7 
            s_link.save()

            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            c_link = shell.CreateShortCut(os.path.join(desktop, "Kraken Control Center.lnk"))
            c_link.Targetpath = FINAL_EXE_PATH
            c_link.Arguments = "--config"
            c_link.IconLocation = FINAL_EXE_PATH
            c_link.save()

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
    print(">>> WebSocket: Новое подключение экрана")
    while True:
        try:
            payload = {
                "cpu_temp": int(psutil.cpu_percent()), 
                "gpu_temp": int(psutil.virtual_memory().percent), 
                "music": await _get_media_data(),
                "theme": current_theme 
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(1)
        except websockets.exceptions.ConnectionClosed:
            print(">>> WebSocket: Экран отключен")
            break
        except Exception as e:
            print(f"Ошибка WS: {e}")
            break

async def change_theme(request):
    # Обработка CORS preflight (OPTIONS)
    if request.method == 'OPTIONS':
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        })

    global current_theme
    current_theme = request.match_info.get('name', "default")
    print(f">>> Тема изменена на: {current_theme}")
    return web.Response(text="OK", headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS"
    })

def start_servers():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Добавлен ping_interval для стабильности
    ws_server = websockets.serve(ws_handler, "127.0.0.1", 8765, ping_interval=20)
    
    app = web.Application()
    app.add_routes([
        web.get('/set_theme/{name}', change_theme),
        web.options('/set_theme/{name}', change_theme)
    ])
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    
    print(">>> Серверы запущены: WS:8765, HTTP:8080")
    loop.run_until_complete(asyncio.gather(ws_server, site.start()))
    loop.run_forever()

if __name__ == "__main__":
    # 1. Установка (только если это EXE билд)
    if getattr(sys, 'frozen', False):
        install_and_setup()

    is_config = "--config" in sys.argv

    # 2. Запуск серверов в фоне
    Thread(target=start_servers, daemon=True).start()

    if is_config:
        print(">>> Запуск окна управления...")
        webview.create_window('Kraken Control Center', CONFIG_URL, width=940, height=620, resizable=False)
        webview.start()
    else:
        print(">>> Сервис работает в фоне...")
        while True: time.sleep(10)
