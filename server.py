import asyncio
import websockets
import json
import winrt.windows.media.control as wmc
import winrt.windows.storage.streams as streams
import base64
import os
import sys
import shutil
import webview
import logging
import winreg # Для работы с реестром
import ctypes # Для уведомлений
from aiohttp import web
from threading import Thread
import time

# Отключаем лишний спам aiohttp
logging.getLogger('aiohttp.access').setLevel(logging.ERROR)

# --- КОНФИГУРАЦИЯ ---
APP_NAME = "KrakenIntegra"
APPDATA_PATH = os.path.join(os.environ['APPDATA'], APP_NAME)
EXE_NAME = "KrakenControl.exe"
FINAL_EXE_PATH = os.path.join(APPDATA_PATH, EXE_NAME)
CONFIG_URL = "https://terpilin.github.io/krakenMedia/src/config.html"

# --- СОСТОЯНИЕ ---
last_track_id = ""
last_cover_b64 = None
current_service = "other"
current_theme = "default"

# --- ЛОГИКА ИНСТАЛЛЯЦИИ И УДАЛЕНИЯ ---
def get_reg_key():
    return r"Software\Microsoft\Windows\CurrentVersion\Uninstall\\" + APP_NAME

def install():
    """Копирует файл, прописывает в автозагрузку и добавляет в список программ Windows"""
    if not os.path.exists(APPDATA_PATH):
        os.makedirs(APPDATA_PATH)
    
    # 1. Копируем себя в AppData, если запущены из другого места
    if os.path.abspath(sys.executable) != os.path.abspath(FINAL_EXE_PATH):
        try:
            shutil.copy2(sys.executable, FINAL_EXE_PATH)
        except: pass

    # 2. Добавляем в реестр для "Установки и удаления программ"
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, get_reg_key())
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Kraken Media Control")
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{FINAL_EXE_PATH}" --uninstall')
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, FINAL_EXE_PATH)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "PotatoPussy Dev")
        winreg.CloseKey(key)
    except: pass

    # 3. Автозагрузка через реестр (надежнее ярлыков)
    try:
        run_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(run_key, APP_NAME, 0, winreg.REG_SZ, f'"{FINAL_EXE_PATH}" --service')
        winreg.CloseKey(run_key)
    except: pass

def uninstall():
    """Полная зачистка реестра"""
    try:
        # Удаляем из автозагрузки
        run_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(run_key, APP_NAME)
        winreg.CloseKey(run_key)
    except: pass

    try:
        # Удаляем из списка программ
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, get_reg_key())
    except: pass

    ctypes.windll.user32.MessageBoxW(0, "Приложение удалено из системы. Файлы в AppData можно удалить вручную.", "Kraken Uninstall", 0x40)
    sys.exit()

# --- МЕДИА ---
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
        elif any(x in source_app for x in ["yandex", "45347", "browser"]): current_service = "yandex"
        
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
            
        return {"title": props.title, "artist": props.artist, "service": current_service, "cover": last_cover_b64}
    except:
        return None

# --- СЕРВЕР ---
async def ws_handler(websocket):
    while True:
        try:
            payload = {
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
        async with websockets.serve(ws_handler, "127.0.0.1", 8765):
            app = web.Application()
            app.add_routes([web.get('/set_theme/{name}', change_theme)])
            runner = web.AppRunner(app); await runner.setup()
            await web.TCPSite(runner, '127.0.0.1', 8080).start()
            await asyncio.Future()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_main())

# --- ТОЧКА ВХОДА ---
if __name__ == "__main__":
    # Если запущен с флагом удаления
    if "--uninstall" in sys.argv:
        uninstall()

    # Если скомпилирован в EXE
    if getattr(sys, 'frozen', False):
        install()

    server_thread = Thread(target=start_servers, daemon=True)
    server_thread.start()

    if "--config" in sys.argv:
        webview.create_window('Kraken Control Center', CONFIG_URL, width=940, height=620)
        webview.start()
    else:
        # Бесконечный цикл для сервиса
        while True:
            time.sleep(10)

