# 🧠 SnapTask — Real-Time Collaborative Task Manager

SnapTask is a real-time collaborative task management web app built with **Flask, Socket.IO, SQLAlchemy, and TailwindCSS**.

Users can create shared workspaces, collaborate on tasks in real time, set deadlines, and track task changes.

## ✨ Features

- 🔐 User authentication
- 🏠 Shared workspaces with membership-based access
- 📋 Create, edit, complete, and delete tasks
- 🕒 Task due dates
- ⚡ Real-time updates with Socket.IO
- 👤 Creator and last-editor tracking
- ⌨️ Live typing indicators
- 🔔 Real-time activity notifications
- 📱 Responsive UI

## 🛠 Tech Stack

**Backend:** Python, Flask, SQLAlchemy, Flask-Login, Flask-SocketIO, Flask-Migrate

**Frontend:** HTML, TailwindCSS, Vanilla JavaScript, Socket.IO Client

**Database:** SQLite / PostgreSQL

**Deployment:** Gunicorn + Eventlet

## 📸 Screenshots

### Landing
![Landing](snaptaskimages/1.jfif)

### Login
![Login](snaptaskimages/2.jfif)

### Workspace Management
![Workspaces](snaptaskimages/3.jfif)

### Task Collaboration
![Tasks](snaptaskimages/5.jfif)


## 🚀 Run Locally

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd SnapTask

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
npm install
npm run build:css

flask db upgrade
python app.py
````

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
```

## 📁 Project Structure

```text
SnapTask/
├── migrations/
├── static/
├── templates/
├── snaptaskimages/
├── app.py
├── auth.py
├── authorize.py
├── models.py
├── room.py
├── extensions.py
└── README.md
```

## 🔮 Future Improvements

* Workspace invitation/acceptance system
* Task priorities and tags
* Search and filtering
* Activity history
* Automated tests
* Email notifications

## 👨‍💻 By Author

Built as a full-stack collaborative application to explore **real-time communication, authentication, relational data modeling, and WebSocket-based collaboration**.
