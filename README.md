# 🖥️ RapidRDP (Python Edition)

**Author** - Rajan Gohil  
**Github:** https://github.com/rajangohil99  

> A gorgeous, high-performance, dark-themed Remote Desktop connection manager built natively in Python using CustomTkinter. 

![RapidRDP Header](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-Dark_Mode-black?style=for-the-badge)
![Security](https://img.shields.io/badge/Security-Windows_Credential_Manager-success?style=for-the-badge&logo=windows)

---

## ✨ Features

- **🎨 Modern Dark UI:** A fully responsive, sleek interface built on top of `CustomTkinter` featuring a fluid grid layout, interactive hover states, and smooth filters.
- **🟢 Live Ping Monitoring:** A highly-efficient, asynchronous background daemon actively pings all configured servers in parallel and displays a real-time Green or Red status indicator directly on the host cards.
- **⚡ Quick Connect Bar:** Need to jump onto a temporary machine quickly? Use the permanent Quick Connect bar to type an IP and instantly fire up an RDP session without building a profile.
- **🏢 Intelligent Domain Credentials:** Store passwords *once* by Domain. Assign a server to a domain, and the app seamlessly securely handles authentication behind the scenes!
- **🔌 Custom Port Support:** Connect to standard or non-standard architectures flawlessly. (e.g., `10.0.0.50:33890`).
- **🛡️ Secure Native Integration:** This tool doesn't hackily embed an old ActiveX container. It strictly interacts via `subprocess` to launch the native, fully-featured Microsoft Terminal Services Client (`mstsc.exe`), and natively leverages memory-mapped Windows Credential Manager commands (`cmdkey.exe`) ensuring top-tier 4K scaling, multi-monitor support, and Enterprise OS-level security.

---

## 🔐 How Security Works (The Vault)

**Passwords are NEVER typed or passed in plaintext to the `mstsc.exe` command-line process!** 

Historically, passing credentials to `mstsc` normally requires vulnerable `.rdp` plain-text files. **This app avoids that completely.**
1. When you specify a Domain or Host password, the tool encodes and stores it inside `rdp_hosts.json`. (Note: This is obfuscation, not encryption. Rely on OS-level ACLs for the JSON file).
2. The instant you attempt a connection, the daemon grabs the credentials and spawns a hidden background invocation of `cmdkey.exe /generic:TERMSRV/<host> /user:<user> /pass:<pass>`.
3. This creates a secure, temporary, authorized token natively directly inside the **Windows Credential Manager**.
4. The tool then launches an empty `mstsc.exe /v:<host>` command.
5. Windows intercepts the connection attempt, realizes its local Secure Vault contains an active `TERMSRV` entry for that IP, and natively logs you in without exposing the flow to external viewers.

---

## 📸 Screenshots

<img src="https://github.com/user-attachments/assets/6a54c962-649e-4beb-9760-a7e60173e6c2" width="900">

<img src="https://github.com/user-attachments/assets/ec5fa30e-9675-4519-bcff-0472d8c2576b" width="500">

---

## 📖 Interface Overview

The interface is broken down into three logical sections:
1. **The Navigation Top Bar:** Includes Global Search, Settings, and the 'New Session' dialogue.
2. **The Library Sidebar:** Actively filters the entire Grid View by specific Domains or Workspaces dynamically. 
3. **The Grid Display:** A responsive array of connection cards automatically branded with smart icons (e.g., Desktop, Linux, Database) depending on context, featuring inline delete controls, interactive hovering, and Real-Time network status lights.

---

## 🚀 Getting Started

### Installation

1. **Clone or Download** the repository to your local machine.
2. Ensure you have Python 3.x installed.
3. Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

### Running the Application

**Option 1: Using the Pre-compiled Executable**
1. Navigate to the [Releases](https://github.com/rajangohil99/RapidRDP/releases) section of this repository.
2. Download the latest `.exe` file.
3. Double-click the executable to launch the application instantly—no Python installation required!

**Option 2: Running from Source**
Simply launch the Python script from your terminal:

```bash
python rdp_manager.py
```

---

<p align="center">
  <i>Built with ❤️ using AI</i>
</p>
