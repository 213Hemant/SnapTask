# 🧠 SnapTask — Real-time Collaborative Task Manager

Welcome to **SnapTask**, a real-time task collaboration app built using **Flask** and **Socket.IO**. It allows users to create shared workspaces (rooms), add and edit tasks collaboratively, and manage deadlines — all in real time ⚡

---

## 🚀 Features

- 🔐 **Authentication**: Sign up and log in securely
- 🏠 **Rooms**: Create and manage shared task rooms
- 📋 **Tasks**: Add, edit, and remove tasks collaboratively
- 🕒 **Due Dates**: Assign deadlines to your tasks
- 💬 **Live Sync**: See updates in real time via WebSockets
- 📱 **Responsive UI**: TailwindCSS-powered design that looks great on all screens

---

## 🛠 Tech Stack

**Backend**:
- 🐍 [Flask]
- 🌐 [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
- 🔒 Flask-Login for user authentication

**Frontend**:
- 🎨 [Tailwind CSS](https://tailwindcss.com/)
- 🧠 Vanilla JavaScript for real-time updates
- 🔌 Socket.IO (client-side) for live communication

---

## 📦 Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/snaptask.git
cd snaptask

# 2. Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
