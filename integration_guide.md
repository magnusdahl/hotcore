# Hotcore Integration Guide

This guide shows you how to integrate the hotcore module into your Python application project.

## Prerequisites

- Python 3.10+
- Redis server running (local or remote)
- hotcore module (built and ready)

## Integration Methods

### Method 1: Install from Built Package (Recommended)

If you have the built wheel file:

```bash
# From your application directory
pip install /path/to/hotcore/dist/hotcore-1.1.0-py3-none-any.whl
```

### Method 2: Install in Editable Mode

From the hotcore directory:

```bash
cd /path/to/hotcore
pip install -e .
```

### Method 3: Add to requirements.txt

Add this line to your project's `requirements.txt`:

```
../hotcore
```

### Method 4: Install from GitHub

If you have a GitHub repository:

```bash
pip install git+https://github.com/yourusername/hotcore.git
```

## Usage in Your Application

### Basic Import

```python
from hotcore import Model

# Initialize the model
model = Model(host='localhost', port=6379, db=0)
```

### Example Application Structure

```
your-app/
├── requirements.txt
├── main.py
├── models/
│   ├── __init__.py
│   └── user_model.py
├── services/
│   ├── __init__.py
│   └── data_service.py
└── config/
    └── settings.py
```

### Example: User Management Service

```python
# services/data_service.py
from hotcore import Model
from typing import Dict, List, Optional

class UserDataService:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.model = Model(host=redis_host, port=redis_port)
        self.users_root_uuid = self._get_or_create_users_root()
    
    def _get_or_create_users_root(self) -> str:
        """Get or create the users root container."""
        # Try to find existing users root
        users_roots = list(self.model.find(type='container', name='Users'))
        if users_roots:
            return users_roots[0]['uuid']
        
        # Create new users root
        users_root = self.model.init({
            'name': 'Users',
            'type': 'container',
            'description': 'Root container for all users'
        })
        created = self.model.create('root', users_root)
        return created['uuid']
    
    def create_user(self, name: str, email: str, role: str = 'user') -> Dict:
        """Create a new user."""
        user = self.model.init({
            'name': name,
            'email': email,
            'type': 'user',
            'role': role,
            'status': 'active'
        })
        return self.model.create(self.users_root_uuid, user)
    
    def get_user(self, user_uuid: str) -> Optional[Dict]:
        """Get a user by UUID."""
        try:
            return self.model.get(user_uuid)
        except:
            return None
    
    def find_users_by_role(self, role: str) -> List[Dict]:
        """Find all users with a specific role."""
        return list(self.model.find(type='user', role=role))
    
    def update_user(self, user_uuid: str, updates: Dict) -> None:
        """Update a user's attributes."""
        updates['uuid'] = user_uuid
        self.model.apply(updates)
    
    def delete_user(self, user_uuid: str) -> bool:
        """Delete a user."""
        user = self.get_user(user_uuid)
        if user:
            self.model.delete(user)
            return True
        return False

### Example: Location-Based Service with Geospatial Features

```python
# services/location_service.py
from hotcore import Model
from typing import Dict, List, Optional, Tuple

class LocationDataService:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.model = Model(host=redis_host, port=redis_port)
        self.locations_root_uuid = self._get_or_create_locations_root()
    
    def _get_or_create_locations_root(self) -> str:
        """Get or create the locations root container."""
        locations_roots = list(self.model.find(type='container', name='Locations'))
        if locations_roots:
            return locations_roots[0]['uuid']
        
        locations_root = self.model.init({
            'name': 'Locations',
            'type': 'container',
            'description': 'Root container for all locations'
        })
        created = self.model.create('root', locations_root)
        return created['uuid']
    
    def create_location(self, name: str, lat: float, lon: float, 
                       location_type: str = 'point', metadata: Dict = None) -> Dict:
        """Create a new location with coordinates.
        
        The location will be automatically added to the geospatial index.
        """
        location = self.model.init({
            'name': name,
            'type': location_type,
            'lat': lat,
            'long': lon,
            'status': 'active'
        })
        
        # Add any additional metadata
        if metadata:
            location.update(metadata)
        
        return self.model.create(self.locations_root_uuid, location)
    
    def find_locations_in_area(self, min_lat: float, max_lat: float,
                              min_lon: float, max_lon: float, location_type: str = "point") -> List[Dict]:
        """Find all locations of a specific type within a geographic bounding box."""
        return self.model.search_bounding_box(min_lat, max_lat, min_lon, max_lon, location_type)
    
    def find_locations_by_type(self, location_type: str) -> List[Dict]:
        """Find all locations of a specific type."""
        return list(self.model.find(type=location_type))
    
    def update_location_coordinates(self, location_uuid: str, 
                                  new_lat: float, new_lon: float) -> None:
        """Update a location's coordinates.
        
        The geospatial index will be automatically updated.
        """
        changes = {
            'uuid': location_uuid,
            'lat': new_lat,
            'long': new_lon
        }
        self.model.apply(changes)
    
    def find_nearby_locations(self, center_lat: float, center_lon: float,
                             radius_km: float = 10.0) -> List[Dict]:
        """Find locations within a radius of a center point.
        
        This uses bounding box search as an approximation.
        """
        # Convert radius to bounding box (rough approximation)
        lat_delta = radius_km / 111.0  # 1 degree ≈ 111 km
        lon_delta = radius_km / (111.0 * abs(center_lat) / 90.0)  # Adjust for latitude
        
        min_lat = center_lat - lat_delta
        max_lat = center_lat + lat_delta
        min_lon = center_lon - lon_delta
        max_lon = center_lon + lon_delta
        
        return self.find_locations_in_area(min_lat, max_lat, min_lon, max_lon, "point")
```

### Example: Project Management Service

```python
# services/project_service.py
from hotcore import Model
from typing import Dict, List, Optional

class ProjectDataService:
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.model = Model(host=redis_host, port=redis_port)
        self.projects_root_uuid = self._get_or_create_projects_root()
    
    def _get_or_create_projects_root(self) -> str:
        """Get or create the projects root container."""
        projects_roots = list(self.model.find(type='container', name='Projects'))
        if projects_roots:
            return projects_roots[0]['uuid']
        
        projects_root = self.model.init({
            'name': 'Projects',
            'type': 'container',
            'description': 'Root container for all projects'
        })
        created = self.model.create('root', projects_root)
        return created['uuid']
    
    def create_project(self, name: str, description: str, owner_email: str) -> Dict:
        """Create a new project."""
        project = self.model.init({
            'name': name,
            'description': description,
            'type': 'project',
            'owner_email': owner_email,
            'status': 'active'
        })
        return self.model.create(self.projects_root_uuid, project)
    
    def find_projects_by_owner(self, owner_email: str) -> List[Dict]:
        """Find all projects owned by a specific user."""
        return list(self.model.find(type='project', owner_email=owner_email))
    
    def find_projects_by_status(self, status: str) -> List[Dict]:
        """Find all projects with a specific status."""
        return list(self.model.find(type='project', status=status))
```

### Example: Main Application

```python
# main.py
from services.data_service import UserDataService
from services.project_service import ProjectDataService

def main():
    # Initialize services
    user_service = UserDataService()
    project_service = ProjectDataService()
    
    # Create some users
    alice = user_service.create_user("Alice Johnson", "alice@example.com", "admin")
    bob = user_service.create_user("Bob Smith", "bob@example.com", "user")
    
    # Create some projects
    project1 = project_service.create_project("Web App", "Modern web application", "alice@example.com")
    project2 = project_service.create_project("Mobile App", "Cross-platform app", "bob@example.com")
    
    # Search and display
    admin_users = user_service.find_users_by_role("admin")
    alice_projects = project_service.find_projects_by_owner("alice@example.com")
    
    print(f"Admin users: {len(admin_users)}")
    print(f"Alice's projects: {len(alice_projects)}")

if __name__ == "__main__":
    main()
```

## Configuration

### Environment Variables

```python
# config/settings.py
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
```

### Docker Integration

```dockerfile
# Dockerfile
FROM python:3.9-slim

# Install Redis client
RUN apt-get update && apt-get install -y redis-tools

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

# Run application
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  app:
    build: .
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

## Testing

### Unit Tests with Mock Redis

```python
# tests/test_user_service.py
import pytest
from unittest.mock import Mock, patch
from services.data_service import UserDataService

@pytest.fixture
def mock_model():
    with patch('services.data_service.Model') as mock:
        yield mock

def test_create_user(mock_model):
    service = UserDataService()
    # Test user creation
    # ... test implementation
```

### Integration Tests with Real Redis

```python
# tests/test_integration.py
import pytest
from services.data_service import UserDataService

@pytest.fixture
def user_service():
    service = UserDataService()
    yield service
    # Cleanup after tests

def test_user_crud_operations(user_service):
    # Test create, read, update, delete operations
    # ... test implementation
```

## Best Practices

1. **Use Services Pattern**: Wrap hotcore operations in service classes
2. **Error Handling**: Implement proper error handling for Redis operations
3. **Connection Management**: Use connection pooling for production
4. **Data Validation**: Validate data before storing in hotcore
5. **Testing**: Use both unit tests (with mocks) and integration tests
6. **Monitoring**: Monitor Redis performance and memory usage

## Troubleshooting

### Common Issues

1. **Redis Connection Error**: Make sure Redis is running
2. **Import Error**: Ensure hotcore is properly installed
3. **Permission Error**: Check Redis connection permissions
4. **Memory Issues**: Monitor Redis memory usage

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed hotcore operations
```

## Performance Considerations

1. **Connection Pooling**: Hotcore uses Redis connection pooling
2. **Indexing**: All attributes are automatically indexed
3. **Search Optimization**: Use specific criteria for faster searches
4. **Memory Management**: Monitor Redis memory usage

## Security

1. **Redis Security**: Configure Redis authentication
2. **Input Validation**: Validate all inputs before storage
3. **Access Control**: Implement proper access controls
4. **Data Encryption**: Consider encrypting sensitive data 
