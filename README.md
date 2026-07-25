# 局域网高速文件传输服务器 / LAN High-Speed File Transfer Server 🚀

一个基于 Python aiohttp 的局域网文件共享工具，支持高速上传/下载、实时在线设备监测和传输动态显示。  
A LAN file sharing tool based on Python aiohttp, supporting high-speed upload/download, real-time online device monitoring, and transfer activity display.

## ✨ 特性 / Features

- **🔥 高速传输 / High-Speed Transfer**: 4MB 大块读写，充分利用千兆局域网带宽  
  4MB chunk read/write to fully utilize gigabit LAN bandwidth
- **📊 实时状态 / Real-time Status**: WebSocket 实时更新在线设备和传输记录  
  WebSocket-based real-time updates for online devices and transfer records
- **⚡ 并行上传 / Parallel Upload**: 支持最多 4 路并发上传  
  Support up to 4 concurrent upload streams
- **🎯 零配置 / Zero Configuration**: 自动检测本机 IP，开箱即用  
  Auto-detect local IP, ready to use out of the box
- **💾 断点续传友好 / Resume-Friendly**: 原始二进制直传，无 multipart 开销  
  Raw binary direct transfer without multipart overhead
- **📱 响应式设计 / Responsive Design**: 适配桌面和移动设备  
  Adapted for desktop and mobile devices

## 📋 系统要求 / System Requirements

- Python 3.8+
- 局域网环境（推荐千兆网络）/ LAN environment (gigabit network recommended)
- 现代浏览器（Chrome、Edge、Firefox、Safari）/ Modern browsers (Chrome, Edge, Firefox, Safari)

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或者自动安装（首次运行会自动安装 aiohttp）：

```bash
python server.py
```

### 2. 启动服务器 / Start Server

```bash
python server.py
```

服务器将自动启动在 `http://127.0.0.1:8082/`，并在局域网内广播 IP 地址。  
The server will automatically start at `http://127.0.0.1:8082/` and broadcast the IP address on the LAN.

### 3. 访问界面 / Access Interface

- **本机访问 / Local Access**: http://127.0.0.1:8082/
- **局域网访问 / LAN Access**: http://{your-lan-ip}:8082/

## 📖 使用说明 / Usage Guide

### 设备命名 / Device Naming

1. 在顶部输入框填写设备名称（例如："家里的 Mac"）  
   Enter device name in the top input field (e.g., "Mac at Home")
2. 点击"保存名称"按钮  
   Click the "Save Name" button
3. 名称将保存在本地 localStorage，下次自动填充  
   The name will be saved in local localStorage and auto-filled next time

### 上传文件 / Upload Files

**方式一：拖拽上传 / Method 1: Drag & Drop**
- 直接将文件或文件夹拖到虚线区域  
  Drag files or folders directly to the dashed area
- 支持多文件同时选择  
  Supports multiple file selection

**方式二：选择文件 / Method 2: Select Files**
- 点击"选择文件"按钮选择单个/多个文件  
  Click "Select Files" button to choose single/multiple files
- 点击"选择文件夹"按钮上传整个文件夹  
  Click "Select Folder" button to upload entire folder

**开始上传 / Start Upload**
- 选中文件后，点击"开始高速上传"  
  After selecting files, click "Start High-Speed Upload"
- 实时显示进度、速度和传输状态  
  Real-time display of progress, speed, and transfer status

### 下载文件 / Download Files

1. 在"可下载文件"列表中找到目标文件  
   Find the target file in the "Downloadable Files" list
2. 点击"高速下载"按钮  
   Click the "High-Speed Download" button
3. 实时显示下载进度和速度  
   Real-time display of download progress and speed

### 清除缓存 / Clear Cache

点击"清除缓存"按钮重置设备标识和本地存储的名称。  
Click the "Clear Cache" button to reset device identifier and locally stored name.

## 🛠️ 技术实现 / Technical Implementation

### 后端架构 / Backend Architecture

- **框架 / Framework**: Python aiohttp
- **并发模型 / Concurrency Model**: asyncio + ThreadPoolExecutor
- **块大小 / Chunk Size**: 4MB（适配大文件传输 / for large file transfer）
- **磁盘缓冲 / Disk Buffer**: 8MB
- **线程池 / Thread Pool**: 8 个工作线程 / 8 worker threads

### 前端特性 / Frontend Features

- **WebSocket**: 实时状态同步（15 秒心跳 / 15s heartbeat）
- **并行上传 / Parallel Upload**: 最多 4 路并发 / up to 4 concurrent streams
- **进度显示 / Progress Display**: XHR 上传/下载实时进度 / real-time XHR upload/download progress
- **本地存储 / Local Storage**: localStorage 保存设备信息 / save device info in localStorage

### API 接口 / API Endpoints

| 端点 / Endpoint | 方法 / Method | 说明 / Description |
|----------------|---------------|-------------------|
| `/` | GET | Web 界面 / Web Interface |
| `/ws` | GET | WebSocket 连接 / WebSocket Connection |
| `/api/state` | GET | 获取完整状态（在线设备、活动记录、文件列表）<br>Get full state (online devices, activity, files) |
| `/api/files` | GET | 获取文件列表 / Get file list |
| `/upload-raw/{path}` | PUT | 高速原始流上传 / High-speed raw stream upload |
| `/upload` | POST | 兼容 multipart 上传 / Multipart-compatible upload |
| `/files/{path}` | GET | 文件下载 / File download |

## 📊 性能优化 / Performance Optimization

1. **大块读写 / Large Chunk Read/Write**: 4MB 传输块，减少系统调用  
   4MB transfer chunks to reduce system calls
2. **线程池写盘 / Thread Pool Disk Write**: 异步读 + 同步写盘，避免阻塞事件循环  
   Async read + sync disk write to avoid blocking event loop
3. **并行上传 / Parallel Upload**: 客户端 4 路并发，服务器端支持多请求处理  
   Client-side 4 concurrent streams, server-side multi-request handling
4. **原始二进制 / Raw Binary**: PUT 直传，避免 multipart 解析开销  
   PUT direct transfer to avoid multipart parsing overhead

## 🔧 配置选项 / Configuration Options

在 `server.py` 中可调整以下参数：  
Adjust the following parameters in `server.py`:

```python
CHUNK = 4 * 1024 * 1024  # 传输块大小（默认 4MB）/ Transfer chunk size (default 4MB)
DISK_BUF = 8 * 1024 * 1024  # 磁盘缓冲（默认 8MB）/ Disk buffer (default 8MB)
IO_POOL = ThreadPoolExecutor(max_workers=8)  # 线程池大小 / Thread pool size
CONCURRENCY = 4  # 客户端并行上传路数 / Client-side parallel upload streams
```

## 📁 目录结构 / Directory Structure

```
.
├── server.py          # 主程序（包含后端和前端 HTML）/ Main program (backend + frontend HTML)
├── requirements.txt   # Python 依赖 / Python dependencies
├── open_firewall_port.bat  # Windows 防火墙开放端口脚本 / Windows firewall port opening script
└── uploads/           # 上传文件存储目录（自动创建）/ Uploaded files storage directory (auto-created)
```

## 🔐 防火墙设置 / Firewall Setup

Windows 用户可运行以下命令开放 8082 端口：  
Windows users can run the following command to open port 8082:

```batch
open_firewall_port.bat
```

或者手动添加入站规则：  
Or manually add an inbound rule:
- 端口 / Port: TCP 8082
- 操作 / Action: 允许连接 / Allow connection

## 🌐 浏览器兼容性 / Browser Compatibility

| 浏览器 / Browser | 最低版本 / Minimum Version |
|------------------|---------------------------|
| Chrome | 70+ |
| Edge | 79+ |
| Firefox | 65+ |
| Safari | 12+ |

## 📝 WebSocket 协议 / WebSocket Protocol

### 客户端发送 / Client Sends

```json
{
  "type": "hello",
  "name": "设备名称 / Device Name",
  "id": "设备 ID / Device ID"
}
```

```json
{
  "type": "rename",
  "name": "新名称 / New Name",
  "id": "设备 ID / Device ID"
}
```

```json
{
  "type": "ping"
}
```

### 服务器返回 / Server Returns

```json
{
  "type": "state",
  "online": [...],
  "online_count": 5,
  "activity": [...],
  "server_time": "12:34:56"
}
```

## 🐛 故障排查 / Troubleshooting

**问题：设备离线频繁 / Issue: Device disconnects frequently**  
- 检查网络连接稳定性 / Check network connection stability  
- 确保浏览器未休眠（标签页保持激活）/ Ensure browser is not sleeping (keep tab active)

**问题：上传速度慢 / Issue: Slow upload speed**  
- 确认使用千兆网络 / Confirm gigabit network usage  
- 关闭其他占用带宽的应用 / Close other bandwidth-intensive apps  
- 尝试增加并发数（修改 `CONCURRENCY`）/ Try increasing concurrency (modify `CONCURRENCY`)

**问题：文件列表不更新 / Issue: File list not updating**  
- 点击"刷新"按钮手动刷新 / Click "Refresh" button to manually refresh  
- 检查 WebSocket 连接状态（顶部显示绿色圆点为正常）/ Check WebSocket connection status (green dot indicates normal)

## 📄 License / 许可证

MIT License - 自由使用、修改和分发  
MIT License - Free to use, modify, and distribute

## 👨‍💻 作者 / Author

**Leechuihui**  
开发日期 / Development Date: 2026-07-21

---

> 💡 **提示 / Tip**: 本工具专为局域网设计，适合家庭、办公室等可信网络环境下的文件共享场景。  
> This tool is designed for LAN environments, suitable for file sharing scenarios in trusted networks such as home or office.
