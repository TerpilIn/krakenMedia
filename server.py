import asyncio
import websockets
import json
import psutil 
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

# Блокируем лишние логи в консоли
logging.getLogger('aiohttp.access').setLevel(logging.ERROR)

# --- КОНФИГУРАЦИЯ ---
APP_NAME = "KrakenIntegra"
APPDATA_PATH = os.path.join(os.environ['APPDATA'], APP_NAME)
EXE_NAME = "KrakenControl.exe"
FINAL_EXE_PATH = os.path.join(APPDATA_PATH, EXE_NAME)
CONFIG_URL = "https://terpilin.github.io/krakenMedia/config.html"

# --- СОСТОЯНИЕ (ПАМЯТЬ СЕРВИСА И ТРЕКА) ---
last_track_id = ""
last_cover_b64 = None
current_service = "other" 
current_theme = "default"

# --- ЛОГИКА ИНСТАЛЛЯЦИИ (ЯРЛЫКИ И ПУТИ) ---
def install_and_setup():
    if not os.path.exists(APPDATA_PATH):
        os.makedirs(APPDATA_PATH)

    current_exe = sys.executable
    if "python.exe" not in current_exe.lower() and os.path.abspath(current_exe) != os.path.abspath(FINAL_EXE_PATH):
        try:
            shutil.copy2(current_exe, FINAL_EXE_PATH)
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')

            # Ярлык в Автозагрузку (Запуск сервиса)
            startup = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
            s_link = shell.CreateShortCut(os.path.join(startup, f"{APP_NAME}_Service.lnk"))
            s_link.Targetpath = FINAL_EXE_PATH
            s_link.Arguments = "--service"
            s_link.WindowStyle = 7 
            s_link.save()

            # Ярлык на Рабочий стол (Запуск конфигуратора)
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            c_link = shell.CreateShortCut(os.path.join(desktop, "Kraken Control Center.lnk"))
            c_link.Targetpath = FINAL_EXE_PATH
            c_link.Arguments = "--config"
            c_link.save()

            os.startfile(FINAL_EXE_PATH, arguments="--service")
            sys.exit()
        except Exception:
            pass

# --- ДАТЧИКИ ТЕМПЕРАТУРЫ (WMI) ---
def get_hardware_stats():
    cpu_val = 0
    gpu_val = 0
    try:
        import wmi
        w = wmi.WMI(namespace="root\\WMI")
        # Получаем реальные градусы CPU через ACPI
        cpu_val = int((w.MSAcpi_ThermalZoneTemperature()[0].CurrentTemperature / 10.0) - 273.15)
    except:
        cpu_val = int(psutil.cpu_percent()) # Фоллбек на нагрузку %

    # Для видеокарты используем RAM как динамический показатель (стабильное решение)
    gpu_val = int(psutil.virtual_memory().percent)
    
    return cpu_val, gpu_val

# --- МЕДИА ДАННЫЕ (С СОХРАНЕНИЕМ ИКОНКИ ТАБЛЕТКИ) ---
async def _get_media_data():
    global last_track_id, last_cover_b64, current_service
    try:
        manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        sessions = manager.get_sessions()
        if not sessions: return None
        
        # Определяем активную сессию (приоритет — PLAYING)
        active_session = next((s for s in sessions if s.get_playback_info().playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING), None)
        if not active_session: active_session = manager.get_current_session() or sessions[0]
        
        source_app = active_session.source_app_user_model_id.lower()
        props = await active_session.try_get_media_properties_async()
        
        # ЛОГИКА "ПРИЛИПАНИЯ" СЕРВИСА: если узнали — меняем, если нет — держим старый
        if "spotify" in source_app: current_service = "spotify"
        elif any(x in source_app for x in ["yandex", "45347"]): current_service = "yandex"
        
        track_id = f"{props.title}_{props.artist}"
        if track_id != last_track_id:
            last_track_id = track_id
            if props.thumbnail:
                stream = await props.thumbnail.open_read_async()
                reader = streams.DataReader(stream.get_input_stream_at(0))
                await reader.load_async(stream.size)
                buffer = bytearray(stream.size)
                reader.read_bytes(buffer)
                last_cover_b64 = base64.b64encode(buffer).decode('utf-8')
            else:
                last_cover_b64 = None
            
        return {
            "title": props.title, 
            "artist": props.artist, 
            "service": current_service, 
            "cover": last_cover_b64
        }
    except:
        return None

# --- СЕРВЕРНАЯ ЛОГИКА (WEBSOCKET + HTTP) ---
async def ws_handler(websocket):
    while True:
        try:
            c, g = get_hardware_stats()
            payload = {
                "cpu_temp": c, 
                "gpu_temp": g, 
                "music": await _get_media_data(),
                "theme": current_theme 
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(1)
        except:
            break

async def change_theme(request):
    global current_theme
    current_theme = request.match_info.get('name', "default")
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

def start_servers():
    async def run_main():
        # Запуск WS для экрана и HTTP для управления
        async with websockets.serve(ws_handler, "127.0.0.1", 8765, ping_interval=20):
            app = web.Application()
            app.add_routes([web.get('/set_theme/{name}', change_theme)])
            runner = web.AppRunner(app); await runner.setup()
            await web.TCPSite(runner, '127.0.0.1', 8080).start()
            await asyncio.Future()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_main())

# --- ЗАПУСК ---
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        install_and_setup()

    server_thread = Thread(target=start_servers, daemon=True)
    server_thread.start()

    if "--config" in sys.argv:
        webview.create_window('Kraken Control Center', CONFIG_URL, width=940, height=620, resizable=False)
        webview.start()
    else:
        # Режим службы в фоне
        while True:
            time.sleep(10)
