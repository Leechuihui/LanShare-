#!/usr/bin/env python3
"""局域网文件服务器 - 高速上传/下载 + 在线状态 + 传输动态

Author: Leechuihui
Date: 2026-07-21
"""

import asyncio
import json
import mimetypes
import os
import re
import socket
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

from aiohttp import WSMsgType, web

# 大块读写，压满千兆局域网
CHUNK = 4 * 1024 * 1024  # 4MB
DISK_BUF = 8 * 1024 * 1024
IO_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="disk")


def format_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


def format_speed(bps: float) -> str:
    return f"{format_size(int(bps))}/s"


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def safe_join(base: str, *parts: str) -> Path:
    root = Path(base).resolve()
    candidate = root.joinpath(*parts).resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError("invalid path")
    return candidate


def normalize_rel(filename: str):
    filename = (filename or "unknown").replace("\\", "/")
    filename = re.sub(r"^([A-Za-z]:)?/+", "", filename)
    parts = [p for p in filename.split("/") if p and p != ".."]
    return parts


class Hub:
    def __init__(self):
        self.clients = {}
        self.activity = deque(maxlen=100)
        self.lock = asyncio.Lock()

    def _online_snapshot(self):
        seen = {}
        for info in self.clients.values():
            key = info.get("id") or info.get("ip")
            prev = seen.get(key)
            if not prev or info.get("last_seen", 0) >= prev.get("last_seen", 0):
                seen[key] = {
                    "id": info.get("id"),
                    "name": info.get("name") or "未命名设备",
                    "ip": info.get("ip"),
                    "joined": info.get("joined"),
                    "last_seen": info.get("last_seen"),
                }
        return sorted(seen.values(), key=lambda x: x.get("name") or "")

    def _payload(self):
        return {
            "type": "state",
            "online": self._online_snapshot(),
            "online_count": len(self._online_snapshot()),
            "activity": list(self.activity),
            "server_time": now_str(),
        }

    async def broadcast(self, message=None):
        data = message or self._payload()
        raw = json.dumps(data, ensure_ascii=False)
        dead = []
        for ws in list(self.clients.keys()):
            try:
                await ws.send_str(raw)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.pop(ws, None)

    async def add(self, ws, ip, ua):
        async with self.lock:
            self.clients[ws] = {
                "id": str(uuid.uuid4())[:8],
                "name": "",
                "ip": ip,
                "ua": (ua or "")[:120],
                "joined": now_str(),
                "last_seen": time.time(),
            }
        await self.add_activity("join", ip, f"{ip} 已连接", "")
        await self.broadcast()

    async def update_name(self, ws, name, client_id=None):
        async with self.lock:
            info = self.clients.get(ws)
            if not info:
                return
            info["name"] = (name or "").strip()[:32] or "未命名设备"
            if client_id:
                info["id"] = client_id[:32]
            info["last_seen"] = time.time()
        await self.broadcast()

    async def heartbeat(self, ws):
        async with self.lock:
            info = self.clients.get(ws)
            if info:
                info["last_seen"] = time.time()

    async def remove(self, ws):
        async with self.lock:
            info = self.clients.pop(ws, None)
        if info:
            label = info.get("name") or info.get("ip")
            await self.add_activity("leave", info.get("ip"), f"{label} 已离线", "")
        await self.broadcast()

    async def add_activity(self, kind, who, text, file="", size=0, speed_h=""):
        item = {
            "time": now_str(),
            "ts": time.time(),
            "kind": kind,
            "who": who,
            "text": text,
            "file": file,
            "size": size,
            "size_h": format_size(size) if size else "",
            "speed_h": speed_h,
        }
        async with self.lock:
            self.activity.appendleft(item)
        if kind in ("upload", "download", "join", "leave"):
            await self.broadcast()


HUB = Hub()


class FileServer:
    def __init__(self, upload_dir="uploads"):
        self.upload_dir = os.path.abspath(upload_dir)
        os.makedirs(self.upload_dir, exist_ok=True)
        print(f"上传/下载目录：{self.upload_dir}")

    def client_label(self, request) -> str:
        name = request.headers.get("X-Device-Name") or request.rel_url.query.get("name")
        ip = request.remote or "?"
        return f"{name} ({ip})" if name else ip

    def list_files(self):
        items = []
        root = Path(self.upload_dir)
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            st = p.stat()
            items.append(
                {
                    "name": rel,
                    "size": st.st_size,
                    "size_h": format_size(st.st_size),
                    "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "url": "/files/" + quote(rel),
                }
            )
        return items

    async def handle_index(self, request):
        return web.Response(text=INDEX_HTML, content_type="text/html", charset="utf-8")

    async def handle_api_state(self, request):
        return web.json_response(
            {
                "online": HUB._online_snapshot(),
                "online_count": len(HUB._online_snapshot()),
                "activity": list(HUB.activity),
                "files": self.list_files(),
            }
        )

    async def handle_api_files(self, request):
        return web.json_response({"files": self.list_files()})

    async def handle_ws(self, request):
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        await HUB.add(ws, request.remote or "?", request.headers.get("User-Agent", ""))
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                        break
                    continue
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                typ = data.get("type")
                if typ in ("hello", "rename"):
                    await HUB.update_name(ws, data.get("name", ""), data.get("id"))
                elif typ == "ping":
                    await HUB.heartbeat(ws)
                    await ws.send_str(json.dumps({"type": "pong", "server_time": now_str()}))
        finally:
            await HUB.remove(ws)
        return ws

    async def _save_stream(self, stream, dest: Path) -> int:
        """大块异步读 + 线程池写盘，尽量吃满带宽。"""
        loop = asyncio.get_running_loop()
        dest.parent.mkdir(parents=True, exist_ok=True)

        def open_file():
            return open(dest, "wb", buffering=DISK_BUF)

        f = await loop.run_in_executor(IO_POOL, open_file)
        size = 0
        try:
            while True:
                chunk = await stream.read(CHUNK)
                if not chunk:
                    break
                await loop.run_in_executor(IO_POOL, f.write, chunk)
                size += len(chunk)
            await loop.run_in_executor(IO_POOL, f.flush)
        finally:
            await loop.run_in_executor(IO_POOL, f.close)
        return size

    async def handle_upload_raw(self, request):
        """PUT /upload-raw/{path} — 原始二进制，无 multipart 开销。"""
        who = self.client_label(request)
        rel = unquote(request.match_info["path"]).replace("\\", "/")
        parts = normalize_rel(rel)
        if not parts:
            raise web.HTTPBadRequest(text="bad path")
        dest = safe_join(self.upload_dir, *parts)
        t0 = time.perf_counter()
        size = await self._save_stream(request.content, dest)
        elapsed = max(time.perf_counter() - t0, 1e-6)
        speed = size / elapsed
        speed_h = format_speed(speed)
        file_rel = "/".join(parts)
        print(f"上传 {speed_h}: {who} -> {file_rel} ({format_size(size)})")
        asyncio.create_task(
            HUB.add_activity(
                "upload",
                who,
                f"{who} 上传了 {file_rel}（{speed_h}）",
                file_rel,
                size,
                speed_h,
            )
        )
        return web.json_response(
            {
                "success": True,
                "file": file_rel,
                "size": size,
                "seconds": round(elapsed, 3),
                "speed": speed,
                "speed_h": speed_h,
            }
        )

    async def handle_upload(self, request):
        """兼容旧 multipart；仍用大块读取。"""
        who = self.client_label(request)
        reader = await request.multipart()
        uploaded = []
        while True:
            field = await reader.next()
            if field is None:
                break
            if not field.filename:
                continue
            parts = normalize_rel(field.filename)
            if not parts:
                continue
            dest = safe_join(self.upload_dir, *parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.perf_counter()
            loop = asyncio.get_running_loop()

            def open_file():
                return open(dest, "wb", buffering=DISK_BUF)

            f = await loop.run_in_executor(IO_POOL, open_file)
            size = 0
            try:
                while True:
                    chunk = await field.read_chunk(size=CHUNK)
                    if not chunk:
                        break
                    await loop.run_in_executor(IO_POOL, f.write, chunk)
                    size += len(chunk)
                await loop.run_in_executor(IO_POOL, f.flush)
            finally:
                await loop.run_in_executor(IO_POOL, f.close)
            elapsed = max(time.perf_counter() - t0, 1e-6)
            speed_h = format_speed(size / elapsed)
            rel = "/".join(parts)
            uploaded.append(rel)
            print(f"上传 {speed_h}: {who} -> {rel}")
            asyncio.create_task(
                HUB.add_activity(
                    "upload", who, f"{who} 上传了 {rel}（{speed_h}）", rel, size, speed_h
                )
            )
        return web.json_response({"success": True, "files": uploaded, "count": len(uploaded)})

    async def handle_download(self, request):
        who = self.client_label(request)
        rel = unquote(request.match_info["path"]).replace("\\", "/")
        parts = normalize_rel(rel)
        try:
            path = safe_join(self.upload_dir, *parts)
        except ValueError:
            raise web.HTTPBadRequest(text="invalid path")
        if not path.is_file():
            raise web.HTTPNotFound(text="file not found")

        file_rel = "/".join(parts)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        t0 = time.perf_counter()

        resp = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": ctype,
                "Content-Length": str(size),
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(path.name)}",
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
        await resp.prepare(request)

        loop = asyncio.get_running_loop()
        sent = 0

        def open_file():
            return open(path, "rb", buffering=DISK_BUF)

        f = await loop.run_in_executor(IO_POOL, open_file)
        try:
            while True:
                chunk = await loop.run_in_executor(IO_POOL, f.read, CHUNK)
                if not chunk:
                    break
                await resp.write(chunk)
                sent += len(chunk)
        finally:
            await loop.run_in_executor(IO_POOL, f.close)

        elapsed = max(time.perf_counter() - t0, 1e-6)
        speed_h = format_speed(sent / elapsed)
        print(f"下载 {speed_h}: {who} <- {file_rel} ({format_size(sent)})")
        asyncio.create_task(
            HUB.add_activity(
                "download",
                who,
                f"{who} 下载了 {file_rel}（{speed_h}）",
                file_rel,
                sent,
                speed_h,
            )
        )
        await resp.write_eof()
        return resp


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>局域网文件传输 · 高速</title>
  <style>
    :root {
      --bg: #f3f0e8; --fg: #2c2c2c; --muted: #6b6b6b; --card: #fff;
      --line: rgba(44,44,44,.1); --online: #1a7f4b; --upload: #1a5f9e;
      --download: #8a5a00; --leave: #888; --speed: #0b5;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: "Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; background: var(--bg); color: var(--fg); min-height: 100vh; padding: 20px; }
    .wrap { max-width: 980px; margin: 0 auto; }
    h1 { font-size: 1.5rem; font-weight: 650; }
    .sub { color: var(--muted); margin: 6px 0 8px; font-size: .92rem; }
    .credit { color: var(--muted); margin: 0 0 18px; font-size: .85rem; letter-spacing: .02em; }
    .credit strong { color: var(--fg); font-weight: 650; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
    .card { background: var(--card); padding: 18px; box-shadow: 0 2px 10px rgba(0,0,0,.05); border: 1px solid var(--line); }
    .card h2 { font-size: 1rem; font-weight: 650; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .badge { font-size: .78rem; font-weight: 600; background: #e8f6ee; color: var(--online); padding: 2px 8px; border-radius: 999px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--online); display: inline-block; margin-right: 6px; box-shadow: 0 0 0 3px rgba(26,127,75,.15); }
    .dot.off { background: #bbb; box-shadow: none; }
    .name-row { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
    .name-row input { flex: 1; min-width: 140px; border: 1px solid var(--line); padding: 10px 12px; font-size: .95rem; }
    button, .btn { background: var(--fg); color: #fff; border: none; padding: 10px 16px; cursor: pointer; font-size: .9rem; }
    button.secondary, a.btn.secondary { background: transparent; color: var(--fg); border: 1px solid var(--fg); text-decoration: none; display: inline-block; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .drop { border: 2px dashed rgba(44,44,44,.22); background: var(--bg); padding: 28px 14px; text-align: center; cursor: pointer; margin-bottom: 12px; }
    .drop:hover, .drop.drag { border-color: var(--fg); background: #ebe6da; }
    input[type=file] { display: none; }
    .btns { display: flex; gap: 8px; flex-wrap: wrap; }
    .progress { height: 10px; background: #e5e0d4; margin-top: 12px; display: none; }
    .progress > i { display: block; height: 100%; width: 0; background: linear-gradient(90deg,#2c2c2c,#1a7f4b); transition: width .1s linear; }
    .status { margin-top: 10px; font-size: .9rem; color: var(--muted); min-height: 1.4em; }
    .speed { color: var(--speed); font-weight: 700; font-variant-numeric: tabular-nums; }
    .list { list-style: none; max-height: 280px; overflow: auto; }
    .list li { padding: 10px 0; border-bottom: 1px solid var(--line); font-size: .92rem; }
    .dev { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
    .dev .meta, .file-meta, .act .time { color: var(--muted); font-size: .8rem; }
    .act .kind { font-size: .72rem; font-weight: 700; margin-right: 6px; }
    .act .kind.upload { color: var(--upload); }
    .act .kind.download { color: var(--download); }
    .act .kind.join { color: var(--online); }
    .act .kind.leave { color: var(--leave); }
    .file-item { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .file-name { flex: 1 1 180px; word-break: break-all; }
    a.dl, button.linkish { color: var(--fg); font-weight: 650; background: none; border: none; padding: 0; text-decoration: underline; cursor: pointer; font-size: .92rem; }
    .empty { color: var(--muted); padding: 8px 0; }
    .ws { font-size: .8rem; color: var(--muted); display: inline-flex; align-items: center; }
    .full { grid-column: 1 / -1; }
    .hint { font-size: .82rem; color: var(--muted); margin-top: 8px; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>局域网文件传输 · 高速</h1>
      <p class="sub">并行上传 · 4MB 块传输 · 实时显示速度 · 在线设备可见传输动态</p>
      <p class="credit">作者 Author：<strong>Leechuihui</strong> · 开发日期：2026-07-21</p>
    </header>

    <div class="name-row card" style="padding:14px 18px;">
      <input id="deviceName" placeholder="设备名称，例如：家里的Mac" maxlength="32" />
      <button type="button" id="saveName">保存名称</button>
      <button type="button" class="secondary" id="clearCache" style="padding:6px 10px;font-size:.8rem;">清除缓存</button>
      <span class="ws" id="wsState"><span class="dot off"></span>连接中…</span>
    </div>

    <div class="grid">
      <div class="card">
        <h2>在线设备 <span class="badge" id="onlineCount">0</span></h2>
        <ul class="list" id="onlineList"><li class="empty">暂无设备在线</li></ul>
      </div>
      <div class="card">
        <h2>传输动态</h2>
        <ul class="list" id="activityList"><li class="empty">还没有上传/下载记录</li></ul>
      </div>

      <div class="card full">
        <h2>上传到共享目录</h2>
        <div class="drop" id="drop"><p>点击选择文件，或拖到这里</p><input type="file" id="fileInput" multiple /></div>
        <div class="btns">
          <button type="button" id="pickFiles">选择文件</button>
          <button type="button" class="secondary" id="pickFolder">选择文件夹</button>
          <button type="button" id="uploadBtn" disabled>开始高速上传</button>
        </div>
        <div class="progress" id="progress"><i id="bar"></i></div>
        <div class="status" id="status"></div>
        <p class="hint">多文件并行上传（最多 4 路）· 使用二进制直传接口</p>
      </div>

      <div class="card full">
        <h2>可下载文件 <button type="button" class="secondary" id="refreshFiles" style="padding:6px 10px;font-size:.8rem;">刷新</button></h2>
        <ul class="list" id="fileList"><li class="empty">暂无文件</li></ul>
        <div class="status" id="dlStatus"></div>
      </div>
    </div>
  </div>

<script>
(() => {
  const $ = (id) => document.getElementById(id);
  const LS_NAME = "lan_device_name";
  const LS_ID = "lan_device_id";
  const CONCURRENCY = 4; // 并行上传路数

  function deviceId() {
    let id = localStorage.getItem(LS_ID);
    if (!id) { id = "d-" + Math.random().toString(36).slice(2, 10); localStorage.setItem(LS_ID, id); }
    return id;
  }
  function deviceName() { return (localStorage.getItem(LS_NAME) || "").trim(); }
  function guessName() {
    const ua = navigator.userAgent || "";
    if (/iPhone|iPad/.test(ua)) return "iPhone/iPad";
    if (/Mac/.test(ua)) return "Mac";
    if (/Android/.test(ua)) return "Android";
    if (/Windows/.test(ua)) return "Windows";
    return "设备";
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  }
  function fmtSize(n) {
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n/1024).toFixed(1) + " KB";
    if (n < 1073741824) return (n/1048576).toFixed(1) + " MB";
    return (n/1073741824).toFixed(2) + " GB";
  }
  function fmtSpeed(bps) { return fmtSize(bps) + "/s"; }

  function setWsState(ok, text) {
    $("wsState").innerHTML = `<span class="dot ${ok?"":"off"}"></span>${text}`;
  }
  function kindLabel(k) {
    return ({upload:"上传",download:"下载",join:"上线",leave:"离线"})[k] || k;
  }

  function renderOnline(list) {
    $("onlineCount").textContent = String(list.length);
    if (!list.length) { $("onlineList").innerHTML = '<li class="empty">暂无设备在线</li>'; return; }
    $("onlineList").innerHTML = list.map(d => `
      <li><div class="dev">
        <div><span class="dot"></span><strong>${escapeHtml(d.name||"未命名设备")}</strong></div>
        <div class="meta">${escapeHtml(d.ip||"")} · ${escapeHtml(d.joined||"")}</div>
      </div></li>`).join("");
  }
  function renderActivity(list) {
    const items = list || [];
    if (!items.length) { $("activityList").innerHTML = '<li class="empty">还没有上传/下载记录</li>'; return; }
    $("activityList").innerHTML = items.map(a => `
      <li class="act">
        <span class="kind ${a.kind}">${kindLabel(a.kind)}</span>
        ${escapeHtml(a.text||"")}
        <span class="time">${escapeHtml(a.time||"")}${a.speed_h? " · <span class='speed'>"+escapeHtml(a.speed_h)+"</span>": ""}${a.size_h&&!a.speed_h? " · "+escapeHtml(a.size_h): ""}</span>
      </li>`).join("");
  }
  function renderFiles(files) {
    if (!files || !files.length) { $("fileList").innerHTML = '<li class="empty">暂无文件</li>'; return; }
    $("fileList").innerHTML = files.map((f, i) => `
      <li class="file-item">
        <span class="file-name">${escapeHtml(f.name)}</span>
        <span class="file-meta">${escapeHtml(f.size_h)} · ${escapeHtml(f.mtime)}</span>
        <button type="button" class="linkish" data-i="${i}">高速下载</button>
      </li>`).join("");
    $("fileList").querySelectorAll("button[data-i]").forEach(btn => {
      btn.onclick = () => downloadFast(files[+btn.dataset.i]);
    });
  }

  // WebSocket
  let ws, pingTimer;
  function connectWs() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => {
      setWsState(true, "实时在线");
      ws.send(JSON.stringify({ type: "hello", name: deviceName() || guessName(), id: deviceId() }));
      clearInterval(pingTimer);
      pingTimer = setInterval(() => { if (ws.readyState === 1) ws.send(JSON.stringify({ type: "ping" })); }, 15000);
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "state") {
          renderOnline(data.online || []);
          renderActivity(data.activity || []);
        }
      } catch {}
    };
    ws.onclose = () => { setWsState(false, "已断开，重连中…"); clearInterval(pingTimer); setTimeout(connectWs, 2000); };
    ws.onerror = () => ws.close();
  }

  $("deviceName").value = deviceName() || guessName();
  $("saveName").onclick = () => {
    const n = $("deviceName").value.trim() || guessName();
    localStorage.setItem(LS_NAME, n);
    $("deviceName").value = n;
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "rename", name: n, id: deviceId() }));
  };

  $("clearCache").onclick = () => {
    localStorage.removeItem(LS_NAME);
    localStorage.removeItem(LS_ID);
    $("deviceName").value = guessName();
    if (ws && ws.readyState === 1) {
      ws.send(JSON.stringify({ type: "rename", name: guessName(), id: deviceId() }));
    }
    $("status").textContent = "已清除本地缓存，设备标识已重置。";
  };

  async function refreshFiles() {
    try {
      const r = await fetch("/api/files");
      const data = await r.json();
      renderFiles(data.files || []);
    } catch {}
  }
  $("refreshFiles").onclick = refreshFiles;

  // ---- 高速并行上传（PUT 原始流）----
  let selected = [];
  const fileInput = $("fileInput");
  const drop = $("drop");

  function setFiles(list) {
    selected = Array.from(list || []);
    $("uploadBtn").disabled = selected.length === 0;
    const total = selected.reduce((s, f) => s + f.size, 0);
    $("status").textContent = selected.length
      ? `已选择 ${selected.length} 个文件，共 ${fmtSize(total)}`
      : "";
  }
  $("pickFiles").onclick = () => { fileInput.removeAttribute("webkitdirectory"); fileInput.click(); };
  $("pickFolder").onclick = () => { fileInput.setAttribute("webkitdirectory", ""); fileInput.click(); };
  drop.onclick = (e) => { if (e.target === drop || e.target.tagName === "P") $("pickFiles").click(); };
  fileInput.onchange = () => setFiles(fileInput.files);
  ["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("drag"); }));
  drop.addEventListener("drop", e => { if (e.dataTransfer.files.length) setFiles(e.dataTransfer.files); });

  function uploadOne(file, onProgress) {
    return new Promise((resolve, reject) => {
      const rel = file.webkitRelativePath || file.name;
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", "/upload-raw/" + encodeURIComponent(rel).replace(/%2F/gi, "/"));
      xhr.setRequestHeader("X-Device-Name", deviceName() || guessName());
      xhr.setRequestHeader("Content-Type", "application/octet-stream");
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded, e.total);
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); }
          catch { resolve({ success: true, size: file.size }); }
        } else reject(new Error("HTTP " + xhr.status));
      };
      xhr.onerror = () => reject(new Error("网络错误"));
      xhr.send(file); // 直接发 File，无 FormData 开销
    });
  }

  async function mapPool(items, limit, worker) {
    const ret = new Array(items.length);
    let i = 0;
    async function run() {
      while (i < items.length) {
        const idx = i++;
        ret[idx] = await worker(items[idx], idx);
      }
    }
    await Promise.all(Array.from({ length: Math.min(limit, items.length) }, run));
    return ret;
  }

  $("uploadBtn").onclick = async () => {
    if (!selected.length) return;
    $("uploadBtn").disabled = true;
    $("progress").style.display = "block";
    const files = selected.slice();
    const totalBytes = files.reduce((s, f) => s + f.size, 0);
    const loadedMap = new Array(files.length).fill(0);
    let ok = 0, fail = 0;
    const t0 = performance.now();

    function tick() {
      const loaded = loadedMap.reduce((a, b) => a + b, 0);
      const elapsed = Math.max((performance.now() - t0) / 1000, 0.001);
      const pct = totalBytes ? Math.min(100, Math.round(loaded / totalBytes * 100)) : 0;
      $("bar").style.width = pct + "%";
      $("status").innerHTML = `上传中 ${pct}% · 已传 ${fmtSize(loaded)} / ${fmtSize(totalBytes)} · <span class="speed">${fmtSpeed(loaded / elapsed)}</span> · 并行 ${CONCURRENCY} 路`;
    }

    await mapPool(files, CONCURRENCY, async (file, idx) => {
      try {
        await uploadOne(file, (loaded) => { loadedMap[idx] = loaded; tick(); });
        loadedMap[idx] = file.size;
        ok++;
      } catch (e) {
        fail++;
        console.error(e);
      }
      tick();
    });

    const elapsed = Math.max((performance.now() - t0) / 1000, 0.001);
    $("bar").style.width = "100%";
    $("status").innerHTML = `完成：成功 ${ok}，失败 ${fail} · 平均 <span class="speed">${fmtSpeed(totalBytes / elapsed)}</span>`;
    selected = []; fileInput.value = "";
    await refreshFiles();
    setTimeout(() => { $("progress").style.display = "none"; $("bar").style.width = "0"; }, 1200);
  };

  // ---- 高速下载（XHR 大文件 + 速度显示）----
  function downloadFast(file) {
    const name = deviceName() || guessName();
    const url = file.url + "?name=" + encodeURIComponent(name);
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url);
    xhr.responseType = "blob";
    const t0 = performance.now();
    $("dlStatus").innerHTML = `正在下载 ${escapeHtml(file.name)}…`;
    xhr.onprogress = (e) => {
      if (!e.lengthComputable) return;
      const elapsed = Math.max((performance.now() - t0) / 1000, 0.001);
      const pct = Math.round(e.loaded / e.total * 100);
      $("dlStatus").innerHTML = `下载 ${escapeHtml(file.name)} ${pct}% · ${fmtSize(e.loaded)} / ${fmtSize(e.total)} · <span class="speed">${fmtSpeed(e.loaded / elapsed)}</span>`;
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const elapsed = Math.max((performance.now() - t0) / 1000, 0.001);
        const blob = xhr.response;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = file.name.split("/").pop();
        a.click();
        URL.revokeObjectURL(a.href);
        $("dlStatus").innerHTML = `已完成 ${escapeHtml(file.name)} · 平均 <span class="speed">${fmtSpeed(blob.size / elapsed)}</span>`;
      } else {
        $("dlStatus").textContent = "下载失败 HTTP " + xhr.status;
      }
    };
    xhr.onerror = () => { $("dlStatus").textContent = "下载网络错误"; };
    xhr.send();
  }

  connectWs();
  refreshFiles();
  setInterval(refreshFiles, 10000);
})();
</script>
</body>
</html>
"""


async def main():
    # 单请求最大约 64GB，适应大文件局域网传输
    app = web.Application(client_max_size=64 * 1024**3)
    server = FileServer("uploads")
    app.router.add_get("/", server.handle_index)
    app.router.add_get("/ws", server.handle_ws)
    app.router.add_get("/api/state", server.handle_api_state)
    app.router.add_get("/api/files", server.handle_api_files)
    app.router.add_put("/upload-raw/{path:.+}", server.handle_upload_raw)
    app.router.add_post("/upload", server.handle_upload)
    app.router.add_get("/files/{path:.+}", server.handle_download)

    lan_ip = "192.168.8.10"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.8.1", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print("=" * 50)
    print("局域网高速文件服务器")
    print(f"本机:   http://127.0.0.1:8082/")
    print(f"局域网: http://{lan_ip}:8082/")
    print(f"块大小: {CHUNK // (1024*1024)}MB  并行写盘线程: 8")
    print("=" * 50)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8082, backlog=256)
    await site.start()
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        import subprocess
        import sys

        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])
    asyncio.run(main())
