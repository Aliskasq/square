# Square

AI чат-бот для Telegram через OpenRouter.

## Установка

```bash
git clone https://github.com/Aliskasq/square.git
cd square

apt install -y python3-venv python3-pip

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
nano .env  # заполни ключи
```

## Запуск

```bash
source venv/bin/activate
python3 main.py
```

## Systemd (автозапуск)

```bash
sudo tee /etc/systemd/system/square.service > /dev/null << 'EOF'
[Unit]
Description=Square AI Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/square
ExecStart=/root/square/venv/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable square
sudo systemctl start square
```

## Логи

```bash
# Онлайн (follow)
sudo journalctl -u square -f

# Последние 100 строк
sudo journalctl -u square -n 100

# За сегодня
sudo journalctl -u square --since today
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Справка |
| `/models` | Выбрать модель (кнопки) |
| `/model` | Текущая модель |
| `/key ключ` | Сменить API ключ |
| `/clear` | Очистить историю |
| `/status` | Статус |
