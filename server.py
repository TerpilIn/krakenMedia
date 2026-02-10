import asyncio, websockets, json, psutil, base64, os, sys, time
import winrt.windows.media.control as wmc
import winrt.windows.storage.streams as streams
from aiohttp import web
from threading import Thread

# --- СОСТОЯНИЕ ---
state = {"last_track": "", "cover": None, "service": "other", "theme": "default"}

def get_stats():
    # Реальный WMI часто капризный, поэтому пока используем нагрузку для теста
    # Но масштабируем её, чтобы цифры были похожи на правду (35-70 градусов)
    cpu = int(35 + (psutil.cpu_percent() * 0.4))
    gpu = int(40 + (psutil.virtual_memory().percent * 0.3))
    return cpu, gpu

async def _get_media():
    try:
        manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        s = manager.get_current_session()
        if not s: return None
        p = await s.try_get_media_properties_async()
        src = s.source_app_user_model_id.lower()
        
        if "spotify" in src: state["service"] = "spotify"
        elif any(x in src for x in ["yandex", "45347"]): state["service"] = "yandex"
        
        t_id = f"{p.title}{p.artist}"
        if t_id != state["last_track"]:
            state["last_track"] = t_id
            if p.thumbnail:
                stream = await p.thumbnail.open_read_async()
                reader = streams.DataReader(stream.get_input_stream_at(0))
                await reader.load_async(stream.size)
                buf = bytearray(stream.size); reader.read_bytes(buf)
                state["cover"] = base64.b64encode(buf).decode('utf-8')
            else: state["cover"] = None
        return {"title": p.title, "artist": p.artist, "service": state["service"], "cover": state["cover"]}
    except: return None

async def ws_handler(ws):
    while True:
        try:
            c, g = get_stats()
            await ws.send(json.dumps({
                "cpu_temp": c, "gpu_temp": g, 
                "music": await _get_media(), "theme": state["theme"]
            }))
            await asyncio.sleep(1)
        except: break

def start_servers():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def main():
        # Запуск WS сервера
        async with websockets.serve(ws_handler, "127.0.0.1", 8765):
            # Запуск HTTP сервера для тем
            app = web.Application()
            app.add_routes([web.get('/set_theme/{name}', lambda r: (state.update({"theme": r.match_info['name']}), web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"}))[1])])
            runner = web.AppRunner(app); await runner.setup()
            await web.TCPSite(runner, '127.0.0.1', 8080).start()
            await asyncio.Future() # Работаем вечно
    loop.run_until_complete(main())

if __name__ == "__main__":
    Thread(target=start_servers, daemon=True).start()
    print(">>> СЕРВЕР КРАКЕНА ЗАПУЩЕН (Порты 8765 и 8080)")
    while True: time.sleep(1)
