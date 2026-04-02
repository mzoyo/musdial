Comprobar si el bot sigue vivo:
```
curl http://localhost:3001/status
```

Si no responde, arrancar el bot:
```
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 && cd /home/theuikri/whatsapp-bot && node bot.js &
```

Despues de arrancarlo, configurar el grupo real:
```
curl -X POST http://localhost:3001/set-group -H "Content-Type: application/json" -d '{"groupId":"120363423591173810@g.us"}'
```
