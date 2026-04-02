import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore } from 'baileys';
import express from 'express';
import qrcode from 'qrcode-terminal';

const app = express();
app.use(express.json());

let sock = null;
let connected = false;
let GROUP_ID = process.env.WHATSAPP_GROUP_ID || '';

const logger = {
    info: () => {}, error: () => {}, warn: () => {},
    debug: () => {}, trace: () => {}, child: () => logger, level: 'silent',
};

async function connectWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth');
    const { version } = await fetchLatestBaileysVersion();
    console.log('[BOT] Version WA:', version.join('.'));

    sock = makeWASocket({
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, logger),
        },
        version,
        logger,
        printQRInTerminal: true,
        browser: ['MUSDIAL Bot', 'Chrome', '22.04.4'],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            qrcode.generate(qr, { small: true });
            console.log('[BOT] Escanea el QR con WhatsApp > Dispositivos vinculados > Vincular dispositivo\n');
        }

        if (connection === 'open') {
            connected = true;
            console.log('[BOT] Conectado a WhatsApp!');
        }

        if (connection === 'close') {
            connected = false;
            const reason = lastDisconnect?.error?.output?.statusCode;
            if (reason !== DisconnectReason.loggedOut) {
                console.log('[BOT] Desconectado, reconectando en 10s...');
                setTimeout(connectWhatsApp, 10000);
            } else {
                console.log('[BOT] Sesion cerrada. Borra la carpeta auth/ y reinicia.');
            }
        }
    });
}

app.get('/status', (req, res) => {
    res.json({ connected, groupId: GROUP_ID });
});

app.get('/groups', async (req, res) => {
    if (!connected) return res.status(503).json({ error: 'No conectado' });
    try {
        const groups = await sock.groupFetchAllParticipating();
        const list = Object.values(groups).map(g => ({
            id: g.id, name: g.subject, participants: g.participants.length,
        }));
        res.json(list);
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/set-group', (req, res) => {
    GROUP_ID = req.body.groupId;
    console.log('[BOT] Grupo configurado:', GROUP_ID);
    res.json({ ok: true, groupId: GROUP_ID });
});

app.post('/send', async (req, res) => {
    if (!connected) return res.status(503).json({ error: 'No conectado' });
    if (!GROUP_ID) return res.status(400).json({ error: 'Grupo no configurado' });
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: 'Falta message' });
    try {
        await sock.sendMessage(GROUP_ID, { text: message });
        console.log('[BOT] Mensaje enviado:', message.substring(0, 50) + '...');
        res.json({ ok: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

const PORT = process.env.BOT_PORT || 3001;
app.listen(PORT, () => {
    console.log('[BOT] API escuchando en puerto ' + PORT);
    connectWhatsApp();
});
