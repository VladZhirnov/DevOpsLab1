#!/usr/bin/env python3
"""
Webhook сервер для GitHub
Реализует автоматическое обновление и деплой приложения
"""

import tempfile
import subprocess
import os
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Конфиг
PORT = 8080
DEPLOY_DIR = "/opt/CattyDevOps/"   # куда клонируем / обновляем проект
REPO_URL = "https://github.com/VladZhirnov/catty-reminders-app.git"  # твой репо
MAIN_DIR = "/home/vboxuser/DevOpsLab1/devops-website"
BRANCH = "master"          # ветка для деплоя

class WebhookHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        # Обрабатываем только /webhook
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8"))
            event_type = self.headers.get("X-GitHub-Event", "unknown")

            print(f"\n🔔 Webhook событие: {event_type} в {datetime.now()}")

            if event_type == "push":
                self._handle_push_event(payload)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except BrokenPipeError:
            print("ℹ️ Клиент разорвал соединение (Broken pipe)")
        except Exception as e:
            print(f"❌ Ошибка обработки webhook: {e}")
            self.send_response(500)
            self.end_headers()

    def _handle_push_event(self, payload):
        subprocess.run(["git", "config", "--global", "--add", "safe.directory", DEPLOY_DIR], check=False) 
        branch_ref = payload.get("ref", "")
        branch = branch_ref.replace("refs/heads/", "")
        print(f"➡️ Push в ветку: {branch}")

        if branch != BRANCH:
            print(f"⏭️ Пропускаем (ветка {branch} не равна {BRANCH})")
            return

        if not os.path.exists(DEPLOY_DIR):
            print("📥 Клонируем репозиторий...")
            subprocess.run(["git", "clone", "-b", BRANCH, REPO_URL, DEPLOY_DIR], check=True)
        else:
            print("🔄 Обновляем репозиторий...")
            subprocess.run(["git", "fetch"], cwd=DEPLOY_DIR, check=True)
            subprocess.run(["git", "checkout", BRANCH], cwd=DEPLOY_DIR, check=True)
            subprocess.run(["git", "pull", "origin", BRANCH], cwd=DEPLOY_DIR, check=True)

        # build.sh (если есть)
        build_script = os.path.join(MAIN_DIR, "build.sh")
        if os.path.exists(build_script):
            print("🔧 Запускаем build.sh...")
            subprocess.run(["bash", build_script], cwd=DEPLOY_DIR, check=True)

        # test.sh (если есть)
        test_script = os.path.join(MAIN_DIR, "test.sh")
        if os.path.exists(test_script):
            print("🧪 Запускаем тесты...")
            try:
                subprocess.run(["bash", test_script], cwd=DEPLOY_DIR, check=True)
                print("✅ Тесты успешны")
            except subprocess.CalledProcessError:
                print("❌ Тесты упали — деплой отменён")
                return

        # deploy.sh (если есть)
        deploy_script = os.path.join(MAIN_DIR, "deploy.sh")
        if os.path.exists(deploy_script):
            print("🚀 Запускаем деплой...")
            subprocess.run(["bash", deploy_script], cwd=DEPLOY_DIR, check=True)
            print("✅ Деплой завершён")
        else:
            print("⚠️ Нет deploy.sh, только код обновлён")

def main():
    print(f"🚀 Запуск Webhook сервера на {PORT}")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("🛑 Остановлен")

if __name__ == "__main__":
    main()