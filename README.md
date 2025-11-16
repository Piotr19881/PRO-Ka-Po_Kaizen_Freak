PRO-Ka-Po – Kaizen Freak Edition 🚀

Multilingual Productivity & Workflow OS for Kaizen Lovers

PRO-Ka-Po – Kaizen Freak Edition is a modular, multilingual desktop app for organizing tasks, projects and daily work – built for people who believe in Kaizen and Lean Management.

Use it as your personal command center for:

daily tasks and projects

habits and focus sessions

notes, emails, files and calls

team collaboration and AI-powered workflows

🌍 Languages & Platforms

Interface languages:

English

Spanish

German

Polish

Chinese

Japanese

Platforms:

Windows 10 / 11

Linux (tested on Ubuntu-based distributions)

macOS (experimental)

🎯 What PRO-Ka-Po Solves

Too many tools for tasks, notes, timers, habits and emails?
→ PRO-Ka-Po centralizes them in one desktop app.

Hard to keep discipline and small improvements every day?
→ Kaizen-oriented modules (Habits, Pomodoro, Kanban) keep you on track.

Need both offline desktop and AI features?
→ Local data + optional AI integrations (OpenAI, Gemini, Claude, Groq).

Want to extend the app for your own workflows?
→ Modular architecture + support for custom modules.

🧩 Core Modules & Features
✅ Tasks & Kanban


Task lists with priorities, tags, due dates and subtasks

Fully configurable table view (columns, filters, quick search)

Kanban board with drag & drop, custom columns, WIP limits and swimlanes

Integration with Pomodoro, notes and habits
<img width="1915" height="1149" alt="image" src="https://github.com/user-attachments/assets/7fee3ab3-b24f-49e0-8034-c65b8256355f" />


🍅 Pomodoro

Classic Pomodoro workflow (e.g. 25/5, editable)

Session history and productivity stats

Sound notifications and desktop pop-ups

Links to tasks / projects for focused work
<img width="1916" height="1145" alt="image" src="https://github.com/user-attachments/assets/7d0bc88e-2398-42c8-b550-4c7fc696799e" />

🎯 Habit Tracker

Monthly calendar view for 6 types of habits (task / counter / checkbox, etc.)

Progress stats and simple analytics

Reminders and synchronization between devices (optional)
<img width="1904" height="1138" alt="image" src="https://github.com/user-attachments/assets/88ba83da-e316-47ca-a2a7-ab2fc755932f" />

📝 Notes

Rich text editor (bold, lists, links, etc.)

Tags, categories and colors

Full-text search

Linking notes to tasks, projects and calls
<img width="1915" height="1144" alt="image" src="https://github.com/user-attachments/assets/a9639640-14b7-4941-82c7-275ee1a689a6" />

⏰ Alarms & Timers

One-time and recurring alarms

Custom sounds and snooze function

Desktop notifications

Can be combined with Pomodoro / tasks
<img width="1916" height="1150" alt="image" src="https://github.com/user-attachments/assets/7ee723c6-deef-45f4-800e-6d2c4299b0d6" />

🤖 AI Module

Optional, configurable AI support (you control your API keys):

Transcription of audio and calls

Smart summaries of notes and documents

Content generation (emails, descriptions, checklists)

Text and sentiment analysis

Works with: OpenAI, Google Gemini, Claude, Groq

📞 CallCryptor – Calls & Transcription

Secure storage of call recordings (local)

AI transcription and automatic summaries

Tags, search and links to tasks/notes

Designed for people working with clients on the phone
<img width="1917" height="1151" alt="image" src="https://github.com/user-attachments/assets/237229ce-0cb1-4fcc-ad5e-98370d8c3fa2" />

👥 TeamWork 

Projects and shared boards

Roles and permissions

Basic team collaboration around tasks and notes
<img width="1918" height="1149" alt="image" src="https://github.com/user-attachments/assets/8fba3b2d-52e2-4e6b-8bc4-b750c20d26a0" />


📁 P-File – File Manager

Manage files and documents directly inside PRO-Ka-Po

Quick preview & simple versioning

Tags and folders for project organization
<img width="1919" height="1150" alt="image" src="https://github.com/user-attachments/assets/b8f42da8-128c-4e0c-b4af-38de09b2404e" />


📧 PRO Mail (planned / experimental)

Multiple email accounts

Filters, rules and templates

AI-assisted replies and drafts
<img width="1913" height="1154" alt="image" src="https://github.com/user-attachments/assets/ad046ed6-c2ac-44fc-9c79-b780b099fbb5" />
<img width="1909" height="1140" alt="image" src="https://github.com/user-attachments/assets/f65775aa-7a25-4ee0-981e-34873e84d5b1" />

🎨 Themes & Customization

Built-in themes: Light, Dark and Custom

Dynamic color schemes – the app adapts to your preferences

Theme engine based on QSS – you can create your own visual themes

Global & module-specific keyboard shortcuts

Configurable sounds, notifications and behavior for each module
<img width="1916" height="1150" alt="image" src="https://github.com/user-attachments/assets/bdc86010-8a87-49e9-9771-99f282c3c862" />


🧱 Modular Architecture & Custom Modules

PRO-Ka-Po is built as a modular system:

Separate modules for: Tasks, Kanban, Notes, Habits, Pomodoro, Alarms, AI, Calls, Files, Mail, Web, TeamWork, Quickboard, Shortcuts and more

Each module has a clear, single responsibility

Modules can be enabled/disabled independently

You can add your own custom modules inside the Modules/ directory

custom logic

custom UI in PyQt6

custom integrations (APIs, internal tools)

This makes PRO-Ka-Po suitable for power-users and companies that want to adapt the app to their own processes.
<img width="1916" height="1148" alt="image" src="https://github.com/user-attachments/assets/572b1151-4112-492c-b8dc-f8fef5340d94" />
<img width="1892" height="1138" alt="image" src="https://github.com/user-attachments/assets/256f9fb0-abbb-455b-810a-aaa6a05ba705" />


🛠 Tech Stack

Python 3.11+

PyQt6 – modern, native desktop GUI

SQLite by default, optional PostgreSQL for server / multi-user setups

SQLAlchemy – ORM

bcrypt – password hashing

Loguru – logging

Optional AI integrations:

OpenAI

Google Gemini

Anthropic Claude

Groq

🚀 Getting Started
Option 1 – Installer (Windows)

For Windows users, you can download a prebuilt installer:

Installer:
https://drive.google.com/file/d/1lmC7J327hnKvGk8zwc86a1M5juNxOKdz/view?usp=drive_link

(Allow running apps from external sources if Windows SmartScreen asks.)

Option 2 – Run from Source (All Platforms)
1. Clone the repository
git clone https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak.git
cd PRO-Ka-Po_Kaizen_Freak

2. Create a virtual environment
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. (Optional) Configure AI & database

Copy config.example.json to config.json (if present)

Add your AI API keys (OpenAI / Gemini / Groq / Claude)

Configure PostgreSQL connection if you want server features

5. Run the app
python main.py

🔐 Security & Privacy

User passwords are hashed using bcrypt

Sensitive data (tokens, API keys, email credentials) are stored securely

Call recordings and personal data are stored locally, not in the repo

Public GitHub repo contains only:

source code

themes, icons, sounds

translations (i18n)

documentation and examples

🗺️ Roadmap (High Level)

Short term:

Improved TeamWork module (roles, projects, shared boards)

Better cloud sync options

More powerful stats & reports (tasks, habits, Pomodoro)

Mid term:

Mobile companion app

Plugin system & marketplace for community modules

Deep calendar integration (Google / Outlook)

Long term:

Real-time collaboration

Voice commands and hands-free control

Advanced automations between modules

🤝 Contributing

Contributions are welcome!

Fork the repo

Create a feature branch:

git checkout -b feature/AmazingFeature


Commit your changes:

git commit -m "feat: Add AmazingFeature"


Push and open a Pull Request

Use conventional commit prefixes: feat:, fix:, docs:, style:, refactor:, test:, chore:.

For bugs or feature ideas, open an Issue or Discussion on GitHub.

📄 License

This project is released under an Open Source license (MIT-style).
See the full license text in the repository.

📧 Contact

Author: Piotr Prokop

Website: www.promirbud.eu

Email: piotr.prokop@promirbud.eu

GitHub: @Piotr19881

🏢 About the Company

Promir-Bud is a manufacturer of modular and container buildings.
PRO-Ka-Po was originally built as an internal tool for managing construction projects and has been opened to the community.

Made with ❤️ for people who treat productivity as a Kaizen journey, not a one-time event.
