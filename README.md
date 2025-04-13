# AI-Enhanced Project Management System

This repository contains the codebase for an AI-enhanced project management system with adaptive scheduling, real-time risk assessment, and predictive resource allocation.

## Development Setup

### Prerequisites
- Python 3.10+
- Git

### Automatic Setup (Windows)
1. Clone the repository
2. Run the setup script:
```
setup.cmd
```

### Manual Setup
1. Clone the repository
2. Create a Python virtual environment:
```
python -m venv venv
```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install backend dependencies:
```
cd backend
pip install -r requirements.txt
```

## Running the Application

### Backend (FastAPI)
1. Activate the virtual environment if not already activated
2. Run the backend server:
```
python backend/main.py
```
3. Access the API at `http://localhost:8001`

## Project Structure
- `backend/` - FastAPI backend application
- `docs/` - Project documentation
  - `docs/setup-guide.md` - Detailed setup instructions
  - `docs/detailed-specs/` - Comprehensive project specifications and roadmap

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, Uvicorn
- **AI/ML**: Ollama, Sentence-Transformers
- **Database**: PostgreSQL, Redis
- **Frontend**: Next.js, ShadCN/ui, Tailwind CSS

## Project Roadmap

For the complete development roadmap, refer to the following documents:
- `ROADMAP.md` - High-level project roadmap
- `docs/detailed-specs/custom-roadmap.md` - Detailed implementation roadmap
- `docs/detailed-specs/odoo-analysis.md` - Comprehensive analysis of project management features 