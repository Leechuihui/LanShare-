**English** | [简体中文](README.zh-CN.md)

# 📡 LAN High-Speed File Transfer Server

[![Python](https://img.shields.io/badge/Python-3.8+-3fb950?logo=python&logoColor=white)](https://python.org) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE) [![Category: Network](https://img.shields.io/badge/Category-Network-58a6ff)](https://github.com/Leechuihui/LanShare-)

A LAN file sharing tool based on Python aiohttp, supporting high-speed upload/download, real-time online device monitoring, and transfer activity display.

## Features

- **High-Speed Transfer**: 4MB chunk read/write with 8 parallel disk I/O threads to fully utilize gigabit LAN bandwidth
- **Real-time Status**: WebSocket-based real-time updates for online devices and transfer records
- **Parallel Upload**: Support up to 4 concurrent upload streams
- **Zero Configuration**: Auto-detect local IP, ready to use out of the box
- **Resume-Friendly**: Raw binary direct transfer without multipart overhead
- **Responsive Design**: Adapted for desktop and mobile devices

## System Requirements

- Python 3.8+
- LAN environment (gigabit network recommended)
- Modern browsers (Chrome, Edge, Firefox, Safari)

## Installation

```bash
pip install -r requirements.txt
```

Or install automatically (aiohttp is installed on first run):

```bash
python server.py
```

### Start Server

```bash
python server.py
```

The server will automatically start at `http://127.0.0.1:8082/` and broadcast the IP address on the LAN.

### Access Interface

- **Local Access**: http://127.0.0.1:8082/
- **LAN Access**: http://{your-lan-ip}:8082/

## 📖 Usage Guide

### Device Naming

1. Enter device name in the top input field (e.g., "Mac at Home")
2. Click the "Save Name" button
3. The name will be saved in local localStorage and auto-filled next time

### Upload Files

**Method 1: Drag & Drop**

- Drag files or folders directly to the dashed area
- Supports multiple file selection

## 📄 License

MIT License - Free to use, modify, and distribute.

## 👨‍💻 Author

**Leechuihui**
Development Date: 2026-07-21

---

> 💡 **Tip**: This tool is designed for LAN environments, suitable for file sharing scenarios in trusted networks such as home or office.
