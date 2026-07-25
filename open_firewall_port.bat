@echo off
chcp 65001 >nul
title 🔓 开放局域网文件传输端口 | Open LAN File Server Port

echo ========================================
echo    🔓 正在开放 8083 端口...
echo    Opening port 8083...
echo ========================================
echo.

netsh advfirewall firewall add rule name="Python File Server 8083" dir=in action=allow protocol=TCP localport=8083 enable=yes

if %ERRORLEVEL% EQU 0 (
    echo ✅ 防火墙规则添加成功！
    echo ✅ Firewall rule added successfully!
    echo.
    echo 📡 现在其他电脑可以访问：
    echo 📡 Now other devices can access:
    echo    中文 | Chinese: http://192.168.8.10:8083/?lang=zh
    echo    English:      http://192.168.8.10:8083/?lang=en
) else (
    echo ❌ 添加失败，请右键此文件选择"以管理员身份运行"
    echo ❌ Failed, please right-click and select "Run as Administrator"
)

echo.
pause
