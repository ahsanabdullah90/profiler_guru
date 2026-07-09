/**
 * PROJECT: WhatsApp Behavioral Pipeline
 * COMPONENT: listener.js (Defensive Version)
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// --- 1. GLOBAL CONFIGURATION ---
const INGEST_URL = 'http://127.0.0.1:8000/api/v1/whatsapp/ingest';
const DATA_DIR = path.join(__dirname, 'Data');
const STATE_FILE = path.join(DATA_DIR, 'sync_state.json');
const LOG_DIR = path.join(__dirname, 'Logs');

[DATA_DIR, LOG_DIR].forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// --- 2. AUDIT LOGGING ---
const sessionID = new Date().toISOString().replace(/[:.]/g, '-');
const logStream = fs.createWriteStream(path.join(LOG_DIR, `listener_session_${sessionID}.log`), { flags: 'a' });

console.log = (msg) => {
    const entry = `${new Date().toLocaleString()} [INFO] ${msg}`;
    logStream.write(entry + '\n');
    process.stdout.write(entry + '\n');
};

// --- 3. INTERACTIVE PROMPT ---
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

function askSyncDays() {
    return new Promise((resolve) => {
        rl.question('\n[PROMPT] How many days of history to check? (e.g., 1, 7, 30): ', (answer) => {
            const days = parseInt(answer) || 0;
            resolve(days);
        });
    });
}

// --- 4. BROWSER INITIALIZATION ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
});

// --- 5. DEFENSIVE PIPELINE LOGIC ---
async function pushToPipeline(message) {
    try {
        const chat = await message.getChat().catch(() => ({ name: 'Unknown', isGroup: false }));
        if (chat.isGroup) return;

        const contact = await message.getContact().catch(() => null);
        
        let quotedBody = null;
        let quotedAuthor = null;

        if (message.hasQuotedMsg) {
            try {
                const quotedMsg = await message.getQuotedMessage();
                quotedBody = quotedMsg.body;
                const qContact = await quotedMsg.getContact().catch(() => null);
                quotedAuthor = qContact ? (qContact.name || qContact.pushname) : quotedMsg.from;
            } catch (quoteErr) {
                console.log(`[WARN] Could not resolve quote details: ${quoteErr.message}`);
            }
        }

        const payload = {
            timestamp: message.timestamp,
            from: message.from,
            fromMe: message.fromMe,
            body: message.body,
            type: message.type,
            contact_name: chat.name || (contact ? (contact.name || contact.pushname) : null) || message.from,
            quoted_body: quotedBody,
            quoted_author: quotedAuthor
        };

        if (message.hasMedia && (message.type === 'ptt' || message.type === 'audio')) {
            const media = await message.downloadMedia().catch(() => null);
            if (media) {
                payload.media_data = media.data;
                payload.media_mimetype = media.mimetype;
            }
        }

        await axios.post(INGEST_URL, payload);
        saveSyncState(message.timestamp);

    } catch (err) {
        console.log(`[ERROR] Dispatch Critical Failure: ${err.message}`);
    }
}

// --- 6. SYNCHRONIZATION ENGINE ---
function saveSyncState(ts) {
    const state = { last_sync_timestamp: ts, last_updated: new Date().toISOString() };
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

async function syncMissingMessages(daysToLookback) {
    const now = Math.floor(Date.now() / 1000);
    const targetTS = now - (daysToLookback * 24 * 60 * 60);
    
    console.log(`[SYNC] Checking last ${daysToLookback} days (Target TS: ${targetTS})`);
    const chats = await client.getChats();

    for (const chat of chats) {
        if (chat.isGroup) continue;
        let missedMessages = [];
        let oldestLoadedId = null;
        let finishedWithChat = false;

        while (!finishedWithChat) {
            const chunk = await chat.fetchMessages({ limit: 40, before: oldestLoadedId }).catch(() => []);
            if (!chunk || chunk.length === 0) break;

            oldestLoadedId = chunk[0].id._serialized;

            for (let i = chunk.length - 1; i >= 0; i--) {
                if (chunk[i].timestamp > targetTS) {
                    missedMessages.push(chunk[i]);
                } else {
                    finishedWithChat = true;
                    break;
                }
            }
            if (missedMessages.length > 1500) break;
        }

        if (missedMessages.length > 0) {
            console.log(`[SYNC] Recovering ${missedMessages.length} messages for ${chat.name}`);
            for (const msg of missedMessages.reverse()) {
                await pushToPipeline(msg);
            }
        }
    }
}

// --- 7. EVENT INITIALIZATION ---
client.on('qr', qr => qrcode.generate(qr, { small: true }));

client.on('ready', async () => {
    console.log('[READY] Bridge Online.');
    const days = await askSyncDays();
    if (days > 0) await syncMissingMessages(days);
    console.log('[READY] System Active (Live Mode).');
});

client.on('message_create', async msg => await pushToPipeline(msg));
client.initialize();