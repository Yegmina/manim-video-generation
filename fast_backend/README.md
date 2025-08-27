# Manim Video Generation FastAPI Backend

A comprehensive, scalable FastAPI backend for generating mathematical animations using Manim. This system provides a robust API for video generation with full CRUD operations, status tracking, and file management.

## 🚀 Features

### Core Functionality
- **Video Generation API**: Create videos from Manim scripts via REST API
- **Async Processing**: Background video generation with status tracking
- **Multiple Formats**: Support for MP4, GIF, and WebM output
- **Quality Settings**: Low, medium, high, and production quality options
- **File Management**: Automatic file storage and cleanup

### Advanced Features
- **Database Integration**: SQLAlchemy with PostgreSQL/SQLite support
- **Authentication**: JWT-based authentication system
- **Rate Limiting**: Configurable request rate limiting
- **CORS Support**: Cross-origin resource sharing configuration
- **Logging**: Comprehensive logging system
- **Health Checks**: System health monitoring
- **Statistics**: Video generation analytics

### Scalability Features
- **Modular Architecture**: Clean separation of concerns
- **Service Layer**: Business logic abstraction
- **Dependency Injection**: Flexible dependency management
- **Background Tasks**: Async processing for video generation
- **Error Handling**: Comprehensive error management
- **Configuration Management**: Environment-based configuration

## 📁 Project Structure

```
fast_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── deps.py            # Dependency injection
│   │   └── v1/
│   │       ├── api.py         # Main API router
│   │       └── endpoints/
│   │           └── videos.py  # Manim2Video endpoints
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   └── database.py        # Database setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Base model
│   │   ├── video.py          # Video generation model
│   │   └── user.py           # User model
│   └── services/
│       ├── __init__.py
│       ├── video_service.py  # Video generation service
│       └── file_service.py   # File management service
├── requirements.txt           # Python dependencies
├── env.example               # Environment variables template
├── run.py                    # Application startup script
├── test_api.py              # API testing script
└── README.md                # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Manim (already installed in parent directory)
- PostgreSQL (optional, SQLite for development)

### Setup

1. **Clone and navigate to the backend directory:**
   ```bash
   cd fast_backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Set up database (SQLite for development):**
   ```bash
   # For SQLite (default)
   echo "DATABASE_URL=sqlite:///./manim_video.db" >> .env
   
   # For PostgreSQL
   echo "DATABASE_URL=postgresql://user:password@localhost/manim_video_db" >> .env
   ```

5. **Set a secret key:**
   ```bash
   echo "SECRET_KEY=your-super-secret-key-here" >> .env
   ```

## 🚀 Running the Application

### Development Mode
```bash
python run.py
```

### Production Mode
```bash
# Set environment to production
export ENVIRONMENT=production

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker (optional)
```bash
# Build image
docker build -t manim-video-api .

# Run container
docker run -p 8000:8000 manim-video-api
```

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Health Check
```bash
GET /health
```

### Manim2Video Generation Endpoints

#### Create Video Generation
```bash
POST /api/v1/manim2video/
Content-Type: application/json

{
  "title": "My Animation",
  "description": "A mathematical animation",
  "script_content": "from manim import *\n\nclass MyScene(Scene):\n    def construct(self):\n        circle = Circle()\n        self.play(Create(circle))",
  "scene_name": "MyScene",
  "quality": "low_quality",
  "format": "mp4",
  "output_name": "my_animation",
  "tags": ["math", "animation"],
  "metadata": {"category": "geometry"}
}
```

#### Get Video Status
```bash
GET /api/v1/manim2video/{video_id}/status
```

#### List Video Generations
```bash
GET /api/v1/manim2video/?skip=0&limit=10&status=completed
```

#### Download Video
```bash
GET /api/v1/manim2video/{video_id}/download
```

#### Cancel Video Generation
```bash
POST /api/v1/manim2video/{video_id}/cancel
```

#### Get Statistics
```bash
GET /api/v1/manim2video/statistics/summary
```

## 🧪 Testing

### Run API Tests
```bash
python test_api.py
```

### Manual Testing with curl

1. **Create a video generation:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/videos/" \
        -H "Content-Type: application/json" \
        -d '{
          "title": "Test Animation",
          "script_content": "from manim import *\n\nclass Test(Scene):\n    def construct(self):\n        circle = Circle()\n        self.play(Create(circle))",
          "scene_name": "Test",
          "quality": "low_quality",
          "format": "mp4"
        }'
   ```

2. **Check status:**
   ```bash
   curl "http://localhost:8000/api/v1/manim2video/1/status"
   ```

3. **Download video:**
   ```bash
   curl "http://localhost:8000/api/v1/manim2video/1/download" -o video.mp4
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | "Manim Video Generation API" |
| `DEBUG` | Debug mode | True |
| `HOST` | Server host | "0.0.0.0" |
| `PORT` | Server port | 8000 |
| `SECRET_KEY` | JWT secret key | Required |
| `DATABASE_URL` | Database connection | Required |
| `UPLOAD_DIR` | Upload directory | "uploads" |
| `VIDEO_OUTPUT_DIR` | Video output directory | "generated_videos" |
| `MAX_FILE_SIZE` | Maximum file size (bytes) | 10485760 |
| `DEFAULT_QUALITY` | Default video quality | "low_quality" |
| `DEFAULT_FORMAT` | Default video format | "mp4" |

### Quality Settings
- `low_quality`: Fast rendering, lower quality
- `medium_quality`: Balanced quality and speed
- `high_quality`: Higher quality, slower rendering
- `production_quality`: Best quality, slowest rendering

### Video Formats
- `mp4`: Most compatible
- `gif`: Animated GIF
- `webm`: Web-optimized format

## 🔧 Development

### Adding New Endpoints

1. **Create endpoint in `app/api/v1/endpoints/`:**
   ```python
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/")
   async def my_endpoint():
       return {"message": "Hello World"}
   ```

2. **Add to main router in `app/api/v1/api.py`:**
   ```python
   from .endpoints import my_endpoint
   
   api_router.include_router(my_endpoint.router, prefix="/my", tags=["my"])
   ```

### Adding New Services

1. **Create service in `app/services/`:**
   ```python
   class MyService:
       def __init__(self):
           pass
       
       async def my_method(self):
           pass
   ```

2. **Use in endpoints:**
   ```python
   from ..services.my_service import MyService
   
   service = MyService()
   result = await service.my_method()
   ```

## 🚀 Deployment

### Production Checklist
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=False`
- [ ] Configure `SECRET_KEY`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis (for caching)
- [ ] Set up reverse proxy (nginx)
- [ ] Configure SSL certificates
- [ ] Set up monitoring and logging

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
Logs are written to `logs/app.log` and console output.

### Metrics
- Request processing time
- Video generation success rate
- Storage usage
- Database connection status

## 🔒 Security

### Authentication
- JWT-based authentication
- Optional authentication for public endpoints
- User role management

### Rate Limiting
- Configurable per-minute and per-hour limits
- IP-based rate limiting

### File Security
- File type validation
- File size limits
- Secure file storage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the logs in `logs/app.log`
- Test with the provided `test_api.py` script

## 🔄 Integration with Frontend

The API is designed to work seamlessly with frontend applications:

```javascript
// Example frontend integration
const createVideo = async (scriptContent) => {
  const response = await fetch('/api/v1/videos/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: 'My Animation',
      script_content: scriptContent,
      scene_name: 'MyScene',
      quality: 'low_quality',
      format: 'mp4'
    })
  });
  
  const video = await response.json();
  return video.id;
};

const checkStatus = async (videoId) => {
  const response = await fetch(`/api/v1/videos/${videoId}/status`);
  return await response.json();
};
```

This FastAPI backend provides a complete, production-ready solution for Manim video generation with comprehensive API endpoints, robust error handling, and scalable architecture.
