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
import logging
from aiohttp import web
from threading import Thread
import time

# Отключаем лишний спам в консоль
logging.getLogger('aiohttp.access').setLevel(logging.ERROR)

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
    if "python.exe" not in current_exe.lower() and os.path.abspath(current_exe) != os.path.abspath(FINAL_EXE_PATH):
        try:
            shutil.copy2(current_exe, FINAL_EXE_PATH)
            # Обязательно: pip install pywin32
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')

            # Путь к EXE с кавычками для защиты от пробелов в путях
            quoted_path = f'"{FINAL_EXE_PATH}"'

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
            c_link.save()

            # Запуск копии из AppData
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
    async def run_main():
        # Запуск WebSocket
        async with websockets.serve(ws_handler, "127.0.0.1", 8765, ping_interval=20):
            # Настройка HTTP
            app = web.Application()
            app.add_routes([
                web.get('/set_theme/{name}', change_theme),
                web.options('/set_theme/{name}', change_theme)
            ])
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '127.0.0.1', 8080)
            await site.start()
            
            print(">>> СЕРВЕРЫ ЗАПУЩЕНЫ: WS:8765, HTTP:8080")
            await asyncio.Future() # Работаем бесконечно

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_main())
    except Exception as e:
        print(f"Цикл серверов остановлен: {e}")

if __name__ == "__main__":
    # 1. Установка
    if getattr(sys, 'frozen', False):
        install_and_setup()

    is_config = "--config" in sys.argv

    # 2. Поток серверов
    server_thread = Thread(target=start_servers, daemon=True)
    server_thread.start()

    time.sleep(1)

    if is_config:
        print(">>> Открытие Kraken Control Center...")
        webview.create_window('Kraken Control Center', CONFIG_URL, width=940, height=620, resizable=False)
        webview.start()
    else:
        print(">>> Kraken работает в фоне. Закройте консоль для выхода.")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
