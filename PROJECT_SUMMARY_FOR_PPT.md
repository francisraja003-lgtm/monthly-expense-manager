# 💰 Monthly Expense Manager - Project Summary for PPT

---

## 📌 PROJECT OVERVIEW

### What is this?
A **complete desktop application** for personal expense and budget management built with Python. Users can track their daily expenses, set monthly budgets, visualize spending patterns, and generate professional PDF reports.

### Key Purpose
Help users manage their money by:
- Recording expenses with categories and dates
- Setting per-category monthly budgets
- Getting alerts when spending exceeds limits
- Viewing spending trends with charts
- Exporting reports for analysis

---

## ✨ CORE FEATURES

### 1. **User Authentication**
- Secure login/signup system
- SHA-256 password hashing (no plaintext storage)
- Per-user data isolation (each user sees only their data)
- Password min 6 characters, username min 3 characters

### 2. **Expense Management**
- ✅ **Add Expenses**: Amount, category, date, description
- ✅ **View All Expenses**: Sortable table with pagination
- ✅ **Edit Expenses**: Inline edit dialog with save/cancel
- ✅ **Delete Expenses**: Delete with confirmation
- ✅ **Search & Filter**: By category, date range, amount range

### 3. **Budget Tracking**
- Set monthly budget limits per category (10 categories available)
- "Quick Set" feature: Apply same budget to all categories at once
- Budget alerts: Red banner when spending exceeds limits
- Progress bars showing spent vs budget for each category

### 4. **Dashboard Analytics**
- **Summary Cards**: Total Spent, Total Budget, Remaining Budget
- **Spending Charts**: 
  - Pie chart (percentage breakdown by category)
  - Bar chart (spent vs budget comparison)
- **Budget Usage Panel**: Visual progress for each category
- **Budget Alerts**: Highlighted red rows for over-budget categories

### 5. **Reports & Export**
- **CSV Export**: Download filtered or full expense data
- **PDF Reports**: Professional multi-page reports with:
  - Header with title and timestamp
  - Summary statistics
  - Embedded spending chart
  - Category breakdown table
  - Full detailed expense table
  - Page numbers and footer

### 6. **Theme Support**
- **Light Mode**: Clean, professional white background
- **Dark Mode**: Eye-friendly dark theme
- One-click toggle (🌙 / ☀️)
- Instant refresh of all UI components

### 7. **Additional Features**
- Currency: All values in Indian Rupees (₹)
- Input validation for amounts, dates, categories
- Amount restrictions (max ₹10 crore)
- Responsive design with scrolling
- Logout without data loss

---

## 🏗 TECHNICAL ARCHITECTURE

### Frontend (GUI)
```
Tkinter + ttk (Python's native GUI library)
├── Login/Signup Window (Full-screen auth)
├── Main Application Window (Tabbed interface)
│   ├── Dashboard Tab
│   ├── Add Expense Tab
│   ├── View/Manage Tab
│   └── Settings Tab
└── Matplotlib (Embedded charts in Dashboard)
```

### Backend (Data Layer)
```
SQLite Database
├── Users Table (username, hashed_password)
├── Expenses Table (amount, category, date, description, user_id)
└── Budgets Table (category, limit, user_id)
```

### Business Logic
```
Python Modules
├── operations.py (All CRUD operations)
├── analytics.py (Budget calculations & chart data)
├── utils.py (Validation & formatting)
└── models.py (Data classes: User, Expense, Budget)
```

### PDF Generation
```
ReportLab Library
└── Creates professional multi-page PDF reports
```

---

## 📊 PROJECT STATISTICS

| Metric | Count |
|--------|-------|
| Total Python Files | 15+ |
| Lines of Code | ~6,000+ |
| Test Coverage | 99 tests, all passing |
| Database Tables | 3 (users, expenses, budgets) |
| GUI Screens | 5 (Login, Dashboard, Add, View, Settings) |
| Categories Available | 10 |
| Features | 20+ |

---

## 🗂 FOLDER STRUCTURE

```
expense_manager_gui/
│
├── main.py                           # Application entry point
│
├── DATABASE LAYER
├── database.py                       # Schema & migrations
├── models.py                         # Data classes
├── operations.py                     # CRUD operations (57 functions)
│
├── BUSINESS LOGIC
├── analytics.py                      # Calculations & analytics
├── utils.py                          # Validators & helpers
├── report_generator.py               # PDF generation
│
├── GUI LAYER
├── gui/
│   ├── theme.py                      # Light/Dark theme manager
│   ├── auth.py                       # Login/Signup window
│   ├── add_expense_tab.py            # Add Expense form
│   ├── view_expenses_tab.py          # View/Manage expenses + Edit dialog
│   ├── dashboard_tab.py              # Dashboard with charts
│   └── settings_tab.py               # Budget settings
│
├── TESTING
├── tests/
│   ├── test_operations.py            # 57 CRUD tests
│   ├── test_analytics.py             # 24 analytics tests
│   └── test_utils.py                 # 18 validation tests
│
├── UTILITIES
├── _check.py                         # Pre-launch validation (25 checks)
├── _gen_sample_pdf.py                # Generate sample PDF
├── _verify_fixes.py                  # Verify bug fixes
│
├── requirements.txt                  # Dependencies
├── pytest.ini                        # Test configuration
└── README.md                         # Documentation
```

---

## 🔧 TECHNOLOGY STACK

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.10+ |
| **GUI Framework** | Tkinter + ttk | Built-in |
| **Database** | SQLite | sqlite3 (stdlib) |
| **Charts** | Matplotlib | 3.5+ |
| **PDF Generation** | ReportLab | 4.2.5 |
| **Date Picker** | tkcalendar | 1.6+ |
| **Testing** | pytest | 8.3+ |
| **OS Support** | Windows, macOS, Linux | Cross-platform |

---

## 💻 HOW IT WORKS

### User Flow

```
1. START APP
   └─> main.py runs
       └─> Creates SQLite database (if first run)
           └─> Opens Login/Signup window

2. USER SIGNS UP / LOGS IN
   └─> Username & password validated
       └─> Password hashed with SHA-256
           └─> User record stored in database
               └─> Main application opens (Dashboard)

3. USER ADDS EXPENSES
   └─> Fills form (amount, category, date, description)
       └─> Saves to database
           └─> Appears in View/Manage tab instantly

4. USER SETS BUDGETS
   └─> Goes to Settings tab
       └─> Sets per-category monthly limits
           └─> Saved to database

5. USER VIEWS DASHBOARD
   └─> Sees summary cards (spent, budget, remaining)
       └─> Views pie/bar charts of spending
           └─> Gets alerts if over budget
               └─> Can download PDF report

6. USER FILTERS & SEARCHES
   └─> Applies filters (category, date, amount)
       └─> Can export to CSV
           └─> Can generate PDF of filtered data

7. USER LOGS OUT
   └─> Returns to Login screen
       └─> All data persists in database
```

---

## 🎯 KEY IMPROVEMENTS MADE

### Bug Fixes
✅ Fixed edit expense save button not working
✅ Fixed date format conversion (dd/mm/yyyy → YYYY-MM-DD)
✅ Added proper error handling and validation
✅ Removed month/year selector from dashboard

### Enhancements
✅ Added comprehensive test coverage (99 tests)
✅ Improved error messages and user feedback
✅ Optimized database queries
✅ Better UI/UX with dark mode support

---

## 📈 DATA MODELS

### User
```
- id: integer (auto-increment)
- username: text (unique)
- password_hash: text (SHA-256)
```

### Expense
```
- id: integer (auto-increment)
- user_id: integer (foreign key)
- amount: real (₹)
- category: text
- date: text (YYYY-MM-DD format)
- description: text
```

### Budget
```
- id: integer (auto-increment)
- user_id: integer (foreign key)
- category: text
- limit: real (monthly limit in ₹)
```

---

## 🧪 TESTING

### Test Coverage: 99 Tests, 100% Passing

**Test Categories:**
- ✅ Operations (CRUD, Auth) - 57 tests
- ✅ Analytics (Calculations, Charts) - 24 tests
- ✅ Utils (Validation, Formatting) - 18 tests

**Run Tests:**
```bash
pytest tests/ -v
```

---

## 🚀 DEPLOYMENT

### System Requirements
- Python 3.10+
- Windows, macOS, or Linux
- 100 MB disk space
- No internet required (offline app)

### Installation Steps
```bash
1. git clone <repo>
2. cd expense_manager_gui
3. python -m venv venv
4. source venv/bin/activate  (or venv\Scripts\activate on Windows)
5. pip install -r requirements.txt
6. python main.py
```

### Database
- Automatically created on first run
- SQLite file: `expense_manager.db`
- Local storage (no cloud sync)

---

## 💡 USE CASES

### Perfect For:
✓ Personal expense tracking
✓ Monthly budget management
✓ Financial planning and analysis
✓ Small business expense recording
✓ Learning Python GUI development
✓ Understanding software architecture

### Typical User Workflow:
1. **Daily**: Add expenses as they happen
2. **Weekly**: Review spending and filter by categories
3. **Monthly**: Check budget status, get alerts
4. **End of Month**: Generate PDF report for record-keeping

---

## 🎓 LEARNING OUTCOMES

This project demonstrates:
- **Desktop GUI Development**: Tkinter fundamentals
- **Database Design**: SQLite schema and CRUD operations
- **Software Architecture**: Separation of concerns (GUI, Logic, Data)
- **Data Visualization**: Matplotlib integration
- **PDF Generation**: ReportLab for reports
- **Testing**: pytest for unit testing
- **Security**: Password hashing and user isolation
- **Error Handling**: Comprehensive validation and error messages
- **Responsive UI**: Theme switching and dynamic updates

---

## 📦 DEPENDENCIES

```
tkinter         # Built-in (GUI)
sqlite3         # Built-in (Database)
matplotlib==3.8.4
tkcalendar==1.6.1
reportlab==4.0.9
pytest==8.3.3
```

---

## 🔒 SECURITY FEATURES

✅ **Password Hashing**: SHA-256 encryption
✅ **User Isolation**: Each user's data is private
✅ **SQL Injection Prevention**: Parameterized queries
✅ **Input Validation**: All inputs validated before saving
✅ **Local Storage**: No data sent to cloud

---

## 📱 RESPONSIVE DESIGN

- **Responsive Layout**: Adapts to window size
- **Scrollable Content**: Long lists handled gracefully
- **Keyboard Navigation**: Full keyboard support
- **Color Accessible**: High contrast in both themes
- **Cross-Platform**: Works on Windows, Mac, Linux

---

## 🎉 ACHIEVEMENTS

✅ Complete working application with all features
✅ 99 unit tests, all passing
✅ Professional PDF report generation
✅ Secure user authentication
✅ Dark mode support
✅ Comprehensive documentation
✅ Git version control
✅ Clean, modular code architecture
✅ Production-ready quality

---

## 🔮 FUTURE ENHANCEMENTS

Possible additions:
- 📊 Advanced analytics (year-over-year comparison)
- 📱 Mobile app version
- ☁️ Cloud sync backup
- 📧 Email report delivery
- 💰 Multi-currency support
- 📈 Investment tracking
- 🔔 Recurring expenses automation
- 📊 Budget forecasting

---

## 📞 SUPPORT & DOCUMENTATION

- **README.md**: Complete user guide
- **Code Comments**: Every module well-documented
- **Tests**: Show usage examples
- **Git Repository**: Full version history

---

## 🏁 CONCLUSION

**Monthly Expense Manager** is a fully functional, production-quality desktop application that demonstrates:
- Professional software development practices
- Modern Python GUI development
- Data persistence and management
- User authentication and security
- Comprehensive testing
- Beautiful UI with theme support

**Ready for presentation, portfolio, or actual use!**

---

**Project Repository**: https://github.com/francisraja003-lgtm/monthly-expense-manager

**Last Updated**: August 30, 2026
