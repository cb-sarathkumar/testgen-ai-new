# TestGen AI - AI-Powered Test Case Generator

A production-ready SaaS application that generates context-aware Cucumber Selenium Java tests using AI. Extract context from Jira, live applications, and documentation, then use LLMs to create comprehensive test suites.

## 🚀 Features

- **AI-Powered Test Generation**: Uses OpenAI GPT-4 and Anthropic Claude for intelligent test creation
- **Context-Aware**: Extracts context from multiple sources (Jira, web apps, documentation)
- **Real-time Progress**: WebSocket-based live updates during test generation
- **Modern UI**: Beautiful React frontend with Tailwind CSS
- **Production Ready**: Complete FastAPI backend with authentication, database, and file management
- **Multiple Integrations**: Support for Jira, OpenAI, and Anthropic APIs

## 🏗️ Architecture

### Backend (FastAPI)
- **Authentication**: JWT-based with bcrypt password hashing
- **Database**: PostgreSQL with async SQLAlchemy
- **Context Extraction**: Jira integration, web scraping, file processing
- **LLM Integration**: OpenAI and Anthropic APIs
- **WebSocket**: Real-time progress tracking
- **File Management**: Generate, store, and serve test files

### Frontend (React + TypeScript)
- **Modern UI**: Tailwind CSS with responsive design
- **State Management**: React Query for server state
- **Real-time Updates**: WebSocket integration
- **Code Preview**: Syntax-highlighted code viewing
- **Authentication**: Protected routes and user management

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker (optional, for database)

## 🛠️ Installation

### Option 1: Docker (Recommended)

#### Quick Start with Docker
```bash
# Clone the repository
git clone <repository-url>
cd testgen-ai

# Set up environment variables
export OPENAI_API_KEY=your-openai-api-key
export ANTHROPIC_API_KEY=your-anthropic-api-key

# Start all services
docker-compose up --build
```

#### Available Docker Commands
```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Start only database
docker-compose up -d postgres
```

### Option 2: Manual Setup

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd testgen-ai
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp config.py .env
# Edit .env with your configuration:
# - DATABASE_URL
# - SECRET_KEY
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
```

#### 3. Database Setup

##### Option A: Using Docker (Recommended)
```bash
# From project root
docker-compose up -d postgres
```

##### Option B: Local PostgreSQL
```bash
# Create database
createdb testgen_db

# Create user
psql -c "CREATE USER testgen WITH PASSWORD 'testgen123';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE testgen_db TO testgen;"
```

#### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 5. Start the Application
```bash
# Terminal 1: Start backend
cd backend
python main.py

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql+asyncpg://testgen:testgen123@localhost:5432/testgen_db
SECRET_KEY=your-super-secret-key-change-this-in-production
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### API Keys Setup

1. **OpenAI**: Get your API key from [platform.openai.com](https://platform.openai.com/api-keys)
2. **Anthropic**: Get your API key from [console.anthropic.com](https://console.anthropic.com/)
3. **Jira**: Get your API token from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens)

## 📖 Usage

### 1. Create Account
- Register a new account or login with existing credentials
- Set up your API integrations (OpenAI, Anthropic, Jira)

### 2. Create Project
- Create a new project for your test suite
- Add application URL and description

### 3. Add Context Sources
- **Jira**: Connect to extract user stories and acceptance criteria
- **Web Application**: Analyze live applications for forms and navigation
- **Documentation**: Upload requirements and API specifications

### 4. Generate Tests
- Configure test generation settings
- Choose LLM provider and model
- Start generation and monitor real-time progress
- Download generated test files

### 5. Review and Use
- Preview generated code with syntax highlighting
- Download individual files or complete ZIP archive
- Integrate into your existing test automation framework

## 🧪 Generated Test Structure

The application generates a complete Maven project structure:

```
generated-tests/
├── pom.xml                           # Maven dependencies
├── src/test/java/
│   ├── TestRunner.java               # Cucumber test runner
│   ├── pages/
│   │   └── BasePage.java            # Base page object
│   └── stepdefinitions/
│       └── FeatureSteps.java        # Step definitions
├── src/test/resources/
│   ├── features/
│   │   └── feature.feature          # Gherkin scenarios
│   └── config.properties            # Test configuration
└── README.md                        # Setup instructions
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Projects
- `GET /api/projects` - List user projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Context Sources
- `GET /api/projects/{id}/contexts` - List context sources
- `POST /api/projects/{id}/contexts` - Add context source
- `DELETE /api/projects/{id}/contexts/{source_id}` - Remove context source

### Test Generation
- `POST /api/projects/{id}/generations` - Start test generation
- `GET /api/projects/{id}/generations` - List generations
- `GET /api/generations/{id}/download` - Download generated files

### Integrations
- `GET /api/integrations` - List user integrations
- `POST /api/integrations` - Add integration
- `DELETE /api/integrations/{id}` - Remove integration

### WebSocket
- `WS /ws/generation/{id}` - Real-time generation progress

## 🚀 Deployment

### Backend Deployment

1. **Environment Setup**:
   ```bash
   # Set production environment variables
   export DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
   export SECRET_KEY=your-production-secret-key
   export OPENAI_API_KEY=your-openai-key
   export ANTHROPIC_API_KEY=your-anthropic-key
   ```

2. **Database Migration**:
   ```bash
   # The application will create tables on startup
   python main.py
   ```

3. **Production Server**:
   ```bash
   # Using Gunicorn
   pip install gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Frontend Deployment

1. **Build for Production**:
   ```bash
   npm run build
   ```

2. **Serve Static Files**:
   ```bash
   # Using nginx or any static file server
   nginx -s reload
   ```


## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📊 Monitoring

- **Health Check**: `GET /health`
- **Metrics**: Application logs and database queries
- **Error Tracking**: Comprehensive error handling and logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the API docs at `/docs`
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join community discussions

## 🎯 Roadmap

- [ ] Support for more test frameworks (Jest, Cypress, Playwright)
- [ ] Advanced context extraction (API documentation, database schemas)
- [ ] Test data generation
- [ ] CI/CD integration
- [ ] Team collaboration features
- [ ] Advanced analytics and reporting

---

**Built with ❤️ for the QA automation community**
