# AI Project Management System

A full-stack application for managing projects with AI assistance.

## Project Structure

```
.
├── backend/           # FastAPI backend
├── frontend/         # Next.js frontend
└── .github/          # GitHub Actions workflows
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Git

## Backend Setup

1. Create a virtual environment:
```bash
cd backend
python -m venv env
.\env\Scripts\activate  # Windows
source env/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the development server:
```bash
uvicorn main:app --reload
```

## Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env.local
# Edit .env.local with your API URL
```

3. Start the development server:
```bash
npm run dev
```

## Development Workflow

1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit them:
```bash
git add .
git commit -m "Description of your changes"
```

3. Push your branch and create a pull request:
```bash
git push origin feature/your-feature-name
```

## Testing

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm test
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment:

- Backend workflow: `.github/workflows/backend.yml`
- Frontend workflow: `.github/workflows/frontend.yml`

The workflows run on:
- Push to main branch
- Pull requests
- Manual triggers

## License

MIT 