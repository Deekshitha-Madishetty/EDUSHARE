# EduShare

<div align="center">
  <p><em>A sustainable academic resource marketplace for GNITS students</em></p>
</div>

## 📚 About EduShare

EduShare is a dedicated digital marketplace designed to streamline the buying, selling, and exchange of academic books and study materials specifically for students at GNITS (Guru Nanak Institute of Technology and Science). This platform addresses the escalating costs of textbooks, fostering a sustainable and collaborative learning environment within the institute.

By promoting resource reuse, EduShare aims to reduce financial burdens and environmental impact, creating a more accessible and eco-conscious educational experience.

## 🌟 Features

- **Secure Community Platform**: Exclusive to GNITS members using official @gnits.ac.in emails
- **Buy, Sell & Donate**: Multiple options for book exchange to suit student needs
- **Structured Transaction Flow**: Clear and trackable book exchange process
- **Real-Time Notifications**: Stay updated on requests, approvals, and completions
- **Transaction History**: "Past Books" log for tracking completed exchanges
- **Book Listings**: Detailed descriptions with image uploads

## 🔧 Technology Stack

### Backend
- **Flask**: Python-based web framework
- **SQLAlchemy**: ORM for database operations
- **Flask-Login**: For user authentication
- **Werkzeug**: Secure password hashing
- **Jinja2**: Template engine for dynamic page rendering

### Frontend
- **HTML/CSS**: Responsive user interface
- **JavaScript**: Interactive elements

### Database
- **SQLite**: Lightweight database for storing book listings and user data

## 🏗️ Architecture

EduShare follows a structured architecture to ensure secure and efficient book exchanges:

1. **User Authentication**: Secure login system restricted to @gnits.ac.in email domains
2. **Book Management**: System for listing, searching, and managing book status
3. **Transaction Lifecycle**: Clearly defined states (pending, accepted, completed)
4. **Notification System**: Real-time alerts for transaction updates
5. **Data Models**: User, Book, Transaction, and Notification models

## 💡 Why EduShare?

Unlike existing platforms like Amazon Marketplace, eBay, Facebook Marketplace, or dedicated book swapping sites, EduShare:

- **Focuses specifically on academic resources**: Tailored for educational materials
- **Creates a closed community**: Enhanced security and trust among GNITS students
- **Emphasizes local exchanges**: No shipping costs or delays
- **Includes donation functionality**: Supporting students with financial constraints
- **Reduces environmental impact**: Promotes sustainable reuse of academic resources

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- pip (Python package installer)

### Installation
1. Clone the repository
   ```
   git clone https://github.com/yourusername/edushare.git
   cd edushare
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Run the application
   ```
   python app.py
   ```

5. Access the application in your browser at `http://localhost:5000`




<div align="center">
  <p>Built with ❤️ for the GNITS community</p>
</div>
