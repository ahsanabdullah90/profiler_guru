# User & Operations Guide

This guide describes how to run Profile Guru, import historical data, start the WhatsApp Bridge, and navigate the application dashboard.

---

## 1. Running the Application (`run.bat`)

Profile Guru includes a robust Windows batch launcher, `run.bat`, located in the root directory. To boot both the FastAPI backend and Next.js frontend:

1. Double-click `run.bat` or run it from a command prompt:
   ```bash
   run.bat
   ```

### Behind the Scenes of the Launcher
The batch script executes several self-healing checks to ensure a smooth launch:
- **Port Cleaning:** Automatically scans and terminates any stale processes listening on port `8000` (FastAPI) and port `3000` (Next.js).
- **Absolute Path Resolution:** Uses `%~dp0` to resolve paths absolutely, allowing you to run the launcher from any terminal directory.
- **Active Health-Check Polling:** Rather than using a blind timeout, it polls the backend's `/api/health` endpoint until the server is fully ready.
- **Synchronized Browser Launch:** Opens Google Chrome pointing to `http://localhost:3000` only after the FastAPI server reports a healthy status.

---

## 2. Ingesting Historical Instagram Exports

Profile Guru relies on manual ZIP data imports to populate your contacts:

1. Log in to your Instagram account in a web browser.
2. Go to **Settings > Your Activity > Download your information**.
3. Select **Download or transfer information**, choose **Some of your information**, check **Messages**, and download as **JSON format** (do not choose HTML).
4. Extract the downloaded ZIP file to a known folder on your computer.
5. In the Profile Guru UI, click the **User Menu** (top-right) and select **Import Panel**.
6. Paste the folder path into the path field (or drag-and-drop the directory if enabled) and click **Start Import**.
7. The progress bar will track message ingestion and background audio transcriptions.

---

## 3. Running the WhatsApp Bridge

The WhatsApp Bridge is an external Node.js agent that forwards live messages to the FastAPI ingest endpoint.

### Initial Launch & Pairing
1. Open a terminal and navigate to the bridge directory:
   ```bash
   cd Whatsapp-Bridge
   ```
2. Start the listener script:
   ```bash
   node listener.js
   ```
3. A large QR code will render directly in your terminal.
4. Open WhatsApp on your mobile phone, navigate to **Linked Devices > Link a Device**, and scan the terminal QR code.
5. Once paired, the console will output `[READY] Bridge Online.`

### Historical Message Synchronization
Upon initial connection, the script will prompt you:
```
[PROMPT] How many days of history to check? (e.g., 1, 7, 30):
```
1. Type the number of days you want to fetch and press **Enter**.
2. The script will scan your active, non-group direct messages, fetch matching chunks, and send them to the backend ingestion queue.
3. Once completed, the bridge runs in **Live Mode**, forwarding all incoming/outgoing messages in real-time.

---

## 4. Dashboard Workspace Walkthrough

The workspace comprises three main functional panes and global utility bars:

### Left Pane: Contact Directory
- Lists your imported contacts sorted by recent activity.
- Visualizes relationship depth badges (`Deep`, `Active`, `Casual`, `Dormant`) computed from true weekly daily message averages.
- Includes a bilingual Urdu/English contact filter bar.

### Middle Pane: Chat History & Analytics
- **Chat Browser:** View monthly conversations. Features Urdu text support, bilingual highlights, and embedded audio player nodes for voice clips.
- **Analytics Tab:** Visualizes a 14-day trend line of daily volume, calculations of true weekly daily average, and weekly vs. monthly comparisons. Every chart includes a data table fallback and CSV export.

### Right Pane: Inspector Panel (`Ctrl/Cmd+I`)
- Toggled on/off via the sidebar icon or keyboard shortcut.
- Displays metadata summary and client/patient identity fields.
- Provides a clinical notes editor with a 1-second auto-save debounce loop.
- Supports adding custom keywords or categorical tags.
