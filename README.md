# ProjectManagerLite

ProjectManagerLite is a professional desktop project management application built with Python and PySide6. 
It supports structured project planning, task scheduling, resource management, cost control, and Earned Value Management (EVM).

---

##  Key Features

### Project Management
- Create and manage multiple projects
- Define project start/end dates and planned budget
- Project-level currency support
- Baseline creation and comparison

### Task Management
- Task creation with planned start, duration, priority, and dependencies
- Actual start/end tracking
- Progress (% complete) updates
- Critical Path scheduling (CPM)

### Resource Management
- Central resource registry with default hourly rate and currency
- Project-specific resource assignment (ProjectResource)
- Planned hours and project-specific rates
- Resource activation/deactivation
- Over-allocation detection and warnings

### Task Assignments
- Assign project resources to tasks
- Allocation percentage per task
- Log actual hours worked
- Automatic labor cost calculation

### Cost Management
- Planned, committed, and actual cost items
- Resource labor costs computed from hours × rate
- Budget vs actual cost tracking
- Cost breakdown by task and resource

### Earned Value Management (EVM)
- Planned Value (PV)
- Earned Value (EV)
- Actual Cost (AC)
- Schedule Variance (SV) and Cost Variance (CV)
- CPI and SPI indicators

### Reporting & Analysis
- Labor cost summaries
- Resource assignment breakdown
- Over-allocation warnings
- Budget utilization overview

---

##  Architecture Overview

- **UI Layer**: PySide6 tabs (Projects, Tasks, Resources, Costs, Reports)
- **Service Layer**: Business logic (TaskService, ReportingService, BaselineService)
- **Domain Models**: Project, Task, Resource, ProjectResource, Assignment
- **Persistence**: SQLAlchemy ORM (SQLite by default)
- **Scheduling Engine**: CPM + Work Calendar
- **Event System**: Domain events for reactive UI updates

---

##  Installation

### Option 1: Installer (Recommended)
1. Download the installer `Setup_ProjectManagerLite_2.0.0.exe`
2. Run the installer and follow on-screen instructions
3. Launch the app from Start Menu or Desktop

### Option 2: From Source (Developers)
```bash
git clone https://github.com/your-username/projectmanagerlite.git
cd projectmanagerlite
python -m venv .env
.env\Scripts\activate
pip install -r requirements.txt
python main_qt.py
```

---

##  Database Behavior

- On first run, the application automatically creates a local SQLite database
- Database migrations are applied automatically
- Each user has an independent local database

---

##  Updates

- Rebuilding the EXE replaces the application binaries
- Existing databases are preserved unless explicitly deleted
- Schema migrations are handled via Alembic

---

##  Tech Stack

- Python 3.11+
- PySide6 (Qt)
- SQLAlchemy
- Alembic
- PyInstaller
- NSIS (Installer)

---

##  Future Enhancements

- Gantt chart visualization
- Multi-user / shared database mode
- What-if scenario planning
- Risk register and issue tracking
- Export reports to Excel/PDF

---

##  License

MIT License

---

## 👤 Author

Developed by **Your Name / Company**  
Contact: your@email.com
