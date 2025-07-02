# FastAPI Video Streaming Service | Clude Prompt:

## Project Requirements: FastAPI Video Streaming Service

**Current Setup:**
- Existing web application: React frontend + Django REST Framework backend
- Course videos currently hosted on YouTube with iframe embedding
- CourseLesson model has a youtube_link field

**New Requirements:**

### Core Functionality:
1. **Admin Video Upload System:**
   - Django admin interface for service administrators
   - Secure login system for admin access
   - Video upload capability (files up to 200MB)
   - Asynchronous processing using Celery for large uploads (100MB+)
   - Upload status tracking with automatic status updates

2. **Video Management:**
   - Generate secure, unique links for uploaded videos after successful processing
   - Admin can copy these links to CourseLesson model's video_link field
   - Video list interface showing previously uploaded videos
   - Delete functionality for uploaded videos

3. **Security & Access Control:**
   - Videos should not be directly downloadable by unauthorized users
   - Secure streaming without exposing direct file URLs
   - Authentication-based access control

4. **Technical Requirements:**
   - Built with FastAPI
   - Scalable architecture
   - Docker & Docker Compose deployment ready
   - Maximum video file size: 200MB
   - Integration with existing React + DRF application

5. **Project Structure:**
   - Well-organized folder structure
   - Easy setup via terminal commands (mkdir, touch, etc.)
   - Clear separation of concerns

### Deliverables:
1. Complete project folder structure
2. Terminal commands for easy project setup
3. FastAPI application with all required endpoints
4. Docker configuration files
5. Integration instructions for existing React + DRF app

**Next Steps:**
After you confirm this structure, we'll build the admin interface using a modern framework, creating the video streaming service step-by-step from scratch.

