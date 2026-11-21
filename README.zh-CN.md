[English](README.md) | **简体中文**

# 📡 局域网高速文件传输服务器

[![Python](https://img.shields.io/badge/Python-3.8+-3fb950?logo=python&logoColor=white)](https://python.org) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE) [![Category: Network](https://img.shields.io/badge/Category-Network-58a6ff)](https://github.com/Leechuihui/LanShare-)

基于 Python aiohttp 的局域网文件共享工具，支持高速上传/下载、实时在线设备监控和传输动态展示。

## 功能特性

- **高速传输**：4MB 大块读写，8 路并行磁盘 I/O 线程，充分跑满千兆局域网带宽
- **实时状态**：基于 WebSocket 的在线设备与传输记录实时更新
- **并行上传**：支持最多 4 路并发上传流
- **零配置**：自动检测本机 IP，开箱即用
- **断点友好**：原始二进制直传，无 multipart 额外开销
- **响应式设计**：适配桌面与移动端设备

## 系统要求

- Python 3.8+
- 局域网环境（推荐千兆网络）
- 现代浏览器（Chrome、Edge、Firefox、Safari）

## 安装

```bash
pip install -r requirements.txt
```

或者自动安装（首次运行会自动安装 aiohttp）：

```bash
python server.py
```

### 启动服务器

```bash
python server.py
```

服务器将自动在 `http://127.0.0.1:8082/` 启动，并在局域网内广播 IP 地址。

### 访问界面

- **本机访问**：http://127.0.0.1:8082/
- **局域网访问**：http://{你的局域网IP}:8082/

## 📖 使用指南

### 设备命名

1. 在顶部输入框中输入设备名称（例如："家里的Mac"）
2. 点击"Save Name"（保存名称）按钮
3. 名称将保存在本地 localStorage 中，下次自动填入

### 上传文件

**方式一：拖放上传**

- 将文件或文件夹直接拖到虚线区域
- 支持多文件选择

## 📄 许可证

MIT License - 可自由使用、修改和分发。

## 👨‍💻 作者

**Leechuihui**
开发日期：2026-07-21

---

> 💡 **提示**：本工具专为局域网设计，适合家庭、办公室等可信网络环境下的文件共享场景。
