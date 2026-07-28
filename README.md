# LAN High-Speed File Transfer Server 

A LAN file sharing tool based on Python aiohttp, supporting high-speed upload/download, real-time online device monitoring, and transfer activity display.

## Features

-  High-Speed Transfer**: 4MB 
  4MB chunk read/write to fully utilize gigabit LAN bandwidth
-  Real-time Status**: WebSocket 
  WebSocket-based real-time updates for online devices and transfer records
-  Parallel Upload**: 
  Support up to 4 concurrent upload streams
-   Zero Configuration**:
  Auto-detect local IP, ready to use out of the box
- Resume-Friendly**: 
  Raw binary direct transfer without multipart overhead
-   Responsive Design**: 
  Adapted for desktop and mobile devices

##System Requirements

- Python 3.8+
- LAN environment (gigabit network recommended)
- Chrome、Edge、Firefox、Safari）/ Modern browsers (Chrome, Edge, Firefox, Safari)



### 

```bash
pip install -r requirements.txt
```

或者自动安装（首次运行会自动安装 aiohttp）：

```bash
python server.py
```

### Start Server

```bash
python server.py
```

 
The server will automatically start at `http://127.0.0.1:8082/` and broadcast the IP address on the LAN.

###  Access Interface

- ** Local Access**: http://127.0.0.1:8082/
- ** LAN Access**: http://{your-lan-ip}:8082/

## 📖  Usage Guide

###  Device Naming

1. 
   Enter device name in the top input field (e.g., "Mac at Home")
2.
   Click the "Save Name" button
3.  
   The name will be saved in local localStorage and auto-filled next time

###  Upload Files

** Method 1: Drag & Drop**
- 
  Drag files or folders directly to the dashed area
-  
  Supports multiple file selection

## 📄 License / 许可证

MIT License - 自由使用、修改和分发  
MIT License - Free to use, modify, and distribute

## 👨‍💻 作者 / Author

**Leechuihui**  
开发日期 / Development Date: 2026-07-21

---

> 💡 **提示 / Tip**: 本工具专为局域网设计，适合家庭、办公室等可信网络环境下的文件共享场景。  
> This tool is designed for LAN environments, suitable for file sharing scenarios in trusted networks such as home or office.
