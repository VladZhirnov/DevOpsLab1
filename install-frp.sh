#!/bin/bash

set -e

echo "🚀 Установка FRP клиента..."
echo "📋 Параметры:"
echo "   Сервер: course.prafdin.ru"
echo "   Токен: devops"
echo "   Пользователь: zhirnov"
echo ""

# Проверяем права суперпользователя
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен запускаться с правами root (sudo)"
   exit 1
fi

# Удаляем старый FRP если есть
echo "🧹 Очищаем старую установку..."
systemctl stop frpc 2>/dev/null || true
rm -f /etc/systemd/system/frpc.service 2>/dev/null || true
rm -f /usr/local/bin/frpc 2>/dev/null || true

# Создаем директорию для FRP
mkdir -p /etc/frp
mkdir -p /var/log/frp

echo "📥 Скачиваем и устанавливаем FRP как systemd сервис..."
curl -fsSL https://gist.github.com/lawrenceching/41244a182307940cc15b45e3c4997346/raw/0576ea85d898c965c3137f7c38f9815e1233e0d1/install-frp-as-systemd-service.sh | bash

# Ждем немного чтобы сервис создался
sleep 3

# Генерируем конфигурацию
echo "⚙️  Генерируем конфигурацию..."
cat > /etc/frp/frpc.toml << EOF
serverAddr = "course.prafdin.ru"
serverPort = 7000
auth.method = "token"
auth.token = "devops"

[[proxies]]
name = "hook-zhirnov"
type = "http"
localIP = "127.0.0.1"
localPort = 8080
customDomains = ["webhook.zhirnov.course.prafdin.ru"]

[[proxies]]
name = "app-zhirnov"
type = "http"
localIP = "127.0.0.1"
localPort = 8181
customDomains = ["app.zhirnov.course.prafdin.ru"]
EOF

echo "✅ Конфигурация сгенерирована в /etc/frp/frpc.toml"

# Устанавливаем права доступа
chown -R root:root /etc/frp
chmod 644 /etc/frp/frpc.toml

echo "🔧 Перезагружаем systemd и запускаем FRP клиент..."
systemctl daemon-reload
systemctl enable frpc
systemctl start frpc

# Даем время на запуск
sleep 2

echo "📊 Проверяем статус FRP клиента..."
if systemctl is-active --quiet frpc; then
    echo "✅ FRP клиент запущен и работает"
    systemctl status frpc --no-pager
else
    echo "❌ FRP клиент не запустился"
    journalctl -u frpc -n 10 --no-pager
    echo "Проверяем наличие сервиса..."
    ls -la /etc/systemd/system/frpc.service 2>/dev/null || echo "Сервис не найден!"
    exit 1
fi

echo ""
echo "✅ FRP клиент установлен и запущен!"
echo ""
echo "🌐 URLs для вашей конфигурации:"
echo "   Webhook URL: http://webhook.zhirnov.course.prafdin.ru"
echo "   App URL: http://app.zhirnov.course.prafdin.ru"
