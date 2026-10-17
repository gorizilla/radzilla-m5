# portal.py – WiFi setup from the phone: the device opens its own WiFi
# ("RadZilla-Setup", WPA2 with a random 8-digit password shown on the
# display) and serves a small page on http://192.168.4.1 where a network
# and its password can be entered. Closes after saving or the timeout.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
import asyncio

AP_NAME = "RadZilla-Setup"
AP_IP = "192.168.4.1"

_PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RadZilla WiFi</title><style>
body{background:#000;color:#f0f0f0;font-family:monospace;margin:0;padding:16px}
h1{color:#ffc800;font-size:20px}label{display:block;margin-top:14px;color:#8c8c8c}
input,select{width:100%;box-sizing:border-box;padding:10px;font-size:16px;
background:#111;color:#f0f0f0;border:1px solid #6e5600;margin-top:4px}
button{margin-top:20px;width:100%;padding:12px;font-size:16px;background:#ffc800;
color:#000;border:0;font-weight:bold}p{color:#8c8c8c}</style></head><body>
<h1>RadZilla WiFi</h1><form method="post" action="/save">
<label>Network</label><select name="ssid">%s</select>
<label>or type the name</label><input name="ssid2" autocomplete="off">
<label>Password</label><input name="pw" type="password" autocomplete="off">
<button type="submit">SAVE</button></form>
<p>Saved networks are used for the time sync only.</p></body></html>"""

_DONE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="background:#000;color:#28dc5a;font-family:monospace;padding:16px">
<h1>Saved: %s</h1><p style="color:#8c8c8c">You can close this page and
reconnect your phone to your normal WiFi.</p></body></html>"""


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _unquote(s):
    s = s.replace("+", " ")
    out = bytearray()
    i = 0
    b = s.encode()
    while i < len(b):
        if b[i] == 37 and i + 2 < len(b):                              # '%'
            try:
                out.append(int(b[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(b[i])
        i += 1
    return out.decode()


def parse_form(body):
    fields = {}
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[_unquote(k)] = _unquote(v)
    return fields


class Portal:
    def __init__(self, ssids, password):
        self.ssids = ssids
        self.password = password
        self.result = None           # (ssid, pw) once saved
        self.server = None
        self.ap = None

    async def start(self):
        import network
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(True)
        self.ap.config(essid=AP_NAME, password=self.password,
                       authmode=network.AUTH_WPA2_PSK, max_clients=2)
        self.server = await asyncio.start_server(self._client, "0.0.0.0", 80)
        print("portal: open,", AP_NAME)

    async def stop(self):
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
        except Exception:
            pass
        try:
            if self.ap:
                self.ap.active(False)
        except Exception:
            pass
        print("portal: closed")

    async def _client(self, reader, writer):
        try:
            line = (await reader.readline()).decode()
            length = 0
            while True:
                h = (await reader.readline()).decode().strip()
                if not h:
                    break
                if h.lower().startswith("content-length:"):
                    length = int(h.split(":", 1)[1])
            if line.startswith("POST /save"):
                body = (await reader.read(min(length, 1024))).decode() if length else ""
                f = parse_form(body)
                ssid = (f.get("ssid2") or "").strip() or f.get("ssid", "")
                if ssid:
                    self.result = (ssid, f.get("pw", ""))
                html = _DONE % _esc(ssid or "-")
            else:
                opts = "".join('<option value="%s">%s</option>' % (_esc(s), _esc(s))
                               for s in self.ssids)
                html = _PAGE % opts
            data = html.encode()
            head = ("HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                    "Content-Length: %d\r\nConnection: close\r\n\r\n" % len(data))
            writer.write(head.encode())
            writer.write(data)
            await writer.drain()
        except Exception as e:
            print("portal:", repr(e))
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
