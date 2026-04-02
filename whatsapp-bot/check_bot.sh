#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null 2>&1

# Comprobar si el bot responde
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/status 2>/dev/null)

if [ "$response" != "200" ]; then
    echo "$(date) - Bot caido, reiniciando..." >> /home/theuikri/whatsapp-bot/bot.log
    cd /home/theuikri/whatsapp-bot
    nohup node bot.js >> bot.log 2>&1 &
fi
