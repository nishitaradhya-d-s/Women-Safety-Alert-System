Women Safety Alert System 🚨
A comprehensive web-based emergency alert system that allows users to trigger SOS alerts with their real-time location, which are instantly sent to pre-registered emergency contacts via SMS. Includes an admin dashboard for monitoring all activities.

🌟 Features
For Users
One-tap SOS – Press the SOS button to immediately send an emergency alert.

Automatic Location Sharing – Captures current GPS coordinates and shares them.

Multiple Emergency Contacts – Register up to two emergency contacts.

SMS Alerts – Sends emergency message with location link via SMS (using SMS gateway).

Persistent Login – Stay logged in forever after registration.

Real-time Location Tracking – Continuously updates location in the background.

For Admins
Complete Dashboard – View all users, active SOS alerts, and recent location updates.

Real-time Monitoring – See online users and active emergencies.

Alert Management – Mark SOS alerts as resolved.

User Management – View all registered users and their details.

Location History – Track user location updates.

🛠️ Tech Stack
Backend: Python Flask

Database: SQLite

Frontend: HTML, CSS, JavaScript (responsive design)

SMS Gateway: Fast2SMS / TextLocal (configurable)

Deployment: PythonAnywhere, Render, Replit, or local server

📋 Prerequisites
Python 3.8+

pip (Python package manager)


🚀 Installation (Local Development)
Clone the repository

bash
git clone https://github.com/yourusername/women-safety-alert.git
cd women-safety-alert
Install dependencies

bash
pip install flask requests
Initialize the database

bash
python app.py
This will create database.db with all required tables.

Run the application

bash
python app.py
The app will be available at http://localhost:5000

📞 Contact
For any queries or suggestions, please open an issue on GitHub or contact the maintainer at nishitaradhya@gmail.com
