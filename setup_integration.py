#!/usr/bin/env python3
"""
Setup script for integrating hotcore into a Python application project.

This script helps you set up hotcore integration in your Python application
by providing various installation and configuration options.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


class HotcoreIntegrationSetup:
    """Helper class for setting up hotcore integration."""

    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.hotcore_path = self._find_hotcore_path()

    def _find_hotcore_path(self) -> Path:
        """Find the hotcore module path."""
        # Check if hotcore is in parent directory
        parent_hotcore = self.project_path.parent / "hotcore"
        if parent_hotcore.exists() and (parent_hotcore / "hotcore").exists():
            return parent_hotcore

        # Check if hotcore is in current directory
        current_hotcore = self.project_path / "hotcore"
        if current_hotcore.exists():
            return current_hotcore

        # Check if hotcore is installed as a package
        try:
            import hotcore

            return Path(hotcore.__file__).parent.parent
        except ImportError:
            pass

        return None

    def install_from_wheel(self, wheel_path: str):
        """Install hotcore from a wheel file."""
        wheel_path = Path(wheel_path)
        if not wheel_path.exists():
            print(f"❌ Wheel file not found: {wheel_path}")
            return False

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", str(wheel_path)],
                check=True,
                cwd=self.project_path,
            )
            print(f"✅ Installed hotcore from wheel: {wheel_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install from wheel: {e}")
            return False

    def install_editable(self):
        """Install hotcore in editable mode."""
        if not self.hotcore_path:
            print("❌ Hotcore path not found")
            return False

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(self.hotcore_path)],
                check=True,
                cwd=self.project_path,
            )
            print(f"✅ Installed hotcore in editable mode from: {self.hotcore_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install in editable mode: {e}")
            return False

    def add_to_requirements(self):
        """Add hotcore to requirements.txt."""
        requirements_file = self.project_path / "requirements.txt"

        if not self.hotcore_path:
            print("❌ Hotcore path not found")
            return False

        # Create requirements.txt if it doesn't exist
        if not requirements_file.exists():
            requirements_file.write_text("")

        # Read current requirements
        current_requirements = requirements_file.read_text().splitlines()

        # Add hotcore if not already present
        hotcore_line = f"../hotcore"
        if hotcore_line not in current_requirements:
            current_requirements.append(hotcore_line)
            requirements_file.write_text("\n".join(current_requirements) + "\n")
            print(f"✅ Added hotcore to {requirements_file}")
        else:
            print(f"ℹ️  Hotcore already in {requirements_file}")

        return True

    def create_example_app(self):
        """Create an example application using hotcore."""
        example_dir = self.project_path / "hotcore_example"
        example_dir.mkdir(exist_ok=True)

        # Create main.py
        main_py = example_dir / "main.py"
        main_content = '''#!/usr/bin/env python3
"""
Example application using hotcore.

This demonstrates basic hotcore usage in a Python application.
"""

from hotcore import Model
import os

def main():
    """Main function demonstrating hotcore usage."""
    print("🚀 Hotcore Example Application")
    print("=" * 40)
    
    # Initialize the model
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    try:
        model = Model(host=redis_host, port=redis_port)
        
        # Create a sample entity
        entity = model.init({})
        entity['name'] = 'Sample Entity'
        entity['type'] = 'example'
        entity['status'] = 'active'
        
        # Create the entity
        created = model.create('root', entity)
        print(f"✅ Created entity: {created['name']} (UUID: {created['uuid']})")
        
        # Retrieve the entity
        retrieved = model.get(created['uuid'])
        print(f"✅ Retrieved entity: {retrieved}")
        
        # Search for entities
        found = list(model.find(type='example'))
        print(f"✅ Found {len(found)} example entities")
        
        print("✅ Example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure Redis is running: redis-server")

if __name__ == "__main__":
    main()
'''
        main_py.write_text(main_content)

        # Create requirements.txt
        requirements_txt = example_dir / "requirements.txt"
        requirements_content = """redis
../hotcore
"""
        requirements_txt.write_text(requirements_content)

        # Create README.md
        readme_md = example_dir / "README.md"
        readme_content = """# Hotcore Example Application

This is an example application demonstrating how to use the hotcore module.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start Redis:
   ```bash
   redis-server
   ```

3. Run the example:
   ```bash
   python main.py
   ```

## What it does

This example demonstrates:
- Connecting to Redis
- Creating entities
- Retrieving entities
- Searching for entities
- Basic error handling

## Next steps

- Modify the example to fit your use case
- Add more complex data structures
- Implement your business logic
"""
        readme_md.write_text(readme_content)

        print(f"✅ Created example application in: {example_dir}")
        return True

    def create_service_template(self):
        """Create a service template for hotcore usage."""
        services_dir = self.project_path / "services"
        services_dir.mkdir(exist_ok=True)

        # Create __init__.py
        init_py = services_dir / "__init__.py"
        init_py.write_text('"""Services package for hotcore integration."""\n')

        # Create data_service.py
        data_service_py = services_dir / "data_service.py"
        data_service_content = '''"""
Data service using hotcore for entity management.

This service provides a clean interface for managing entities
using the hotcore module.
"""

from hotcore import Model
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataService:
    """Base data service using hotcore."""
    
    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        """Initialize the data service."""
        self.model = Model(host=redis_host, port=redis_port)
        self.root_uuid = self._get_or_create_root()
    
    def _get_or_create_root(self) -> str:
        """Get or create the root container for this service."""
        # Try to find existing root
        roots = list(self.model.find(type='container', name=self.__class__.__name__))
        if roots:
            return roots[0]['uuid']
        
        # Create new root
        root = self.model.init({
            'name': self.__class__.__name__,
            'type': 'container',
            'description': f'Root container for {self.__class__.__name__}'
        })
        created = self.model.create('root', root)
        return created['uuid']
    
    def create_entity(self, entity_data: Dict) -> Dict:
        """Create a new entity."""
        entity = self.model.init(entity_data)
        return self.model.create(self.root_uuid, entity)
    
    def get_entity(self, entity_uuid: str) -> Optional[Dict]:
        """Get an entity by UUID."""
        try:
            return self.model.get(entity_uuid)
        except Exception as e:
            logger.error(f"Error getting entity {entity_uuid}: {e}")
            return None
    
    def find_entities(self, **criteria) -> List[Dict]:
        """Find entities matching criteria."""
        return list(self.model.find(**criteria))
    
    def update_entity(self, entity_uuid: str, updates: Dict) -> None:
        """Update an entity's attributes."""
        updates['uuid'] = entity_uuid
        self.model.apply(updates)
    
    def delete_entity(self, entity_uuid: str) -> bool:
        """Delete an entity."""
        entity = self.get_entity(entity_uuid)
        if entity:
            self.model.delete(entity)
            return True
        return False


class UserService(DataService):
    """Service for managing user entities."""
    
    def create_user(self, name: str, email: str, role: str = 'user') -> Dict:
        """Create a new user."""
        return self.create_entity({
            'name': name,
            'email': email,
            'type': 'user',
            'role': role,
            'status': 'active'
        })
    
    def find_users_by_role(self, role: str) -> List[Dict]:
        """Find all users with a specific role."""
        return self.find_entities(type='user', role=role)
    
    def find_active_users(self) -> List[Dict]:
        """Find all active users."""
        return self.find_entities(type='user', status='active')


class ProjectService(DataService):
    """Service for managing project entities."""
    
    def create_project(self, name: str, description: str, owner_email: str) -> Dict:
        """Create a new project."""
        return self.create_entity({
            'name': name,
            'description': description,
            'type': 'project',
            'owner_email': owner_email,
            'status': 'active'
        })
    
    def find_projects_by_owner(self, owner_email: str) -> List[Dict]:
        """Find all projects owned by a specific user."""
        return self.find_entities(type='project', owner_email=owner_email)
    
    def find_active_projects(self) -> List[Dict]:
        """Find all active projects."""
        return self.find_entities(type='project', status='active')
'''
        data_service_py.write_text(data_service_content)

        print(f"✅ Created service template in: {services_dir}")
        return True

    def check_installation(self):
        """Check if hotcore is properly installed."""
        try:
            import hotcore
            from hotcore import Model

            print("✅ Hotcore is properly installed and importable")
            return True
        except ImportError as e:
            print(f"❌ Hotcore import failed: {e}")
            return False

    def run_tests(self):
        """Run hotcore tests to verify installation."""
        if not self.hotcore_path:
            print("❌ Hotcore path not found")
            return False

        try:
            subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v"],
                check=True,
                cwd=self.hotcore_path,
            )
            print("✅ Hotcore tests passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Hotcore tests failed: {e}")
            return False


def main():
    """Main function for the setup script."""
    parser = argparse.ArgumentParser(description="Setup hotcore integration")
    parser.add_argument("--project-path", help="Path to the project directory")
    parser.add_argument("--wheel-path", help="Path to hotcore wheel file")
    parser.add_argument(
        "--install-editable", action="store_true", help="Install in editable mode"
    )
    parser.add_argument(
        "--add-to-requirements", action="store_true", help="Add to requirements.txt"
    )
    parser.add_argument(
        "--create-example", action="store_true", help="Create example application"
    )
    parser.add_argument(
        "--create-service-template", action="store_true", help="Create service template"
    )
    parser.add_argument(
        "--check-installation", action="store_true", help="Check installation"
    )
    parser.add_argument("--run-tests", action="store_true", help="Run hotcore tests")
    parser.add_argument("--all", action="store_true", help="Run all setup steps")

    args = parser.parse_args()

    setup = HotcoreIntegrationSetup(args.project_path)

    if args.all:
        # Run all setup steps
        setup.install_editable()
        setup.add_to_requirements()
        setup.create_example_app()
        setup.create_service_template()
        setup.check_installation()
    else:
        # Run specific steps
        if args.wheel_path:
            setup.install_from_wheel(args.wheel_path)
        if args.install_editable:
            setup.install_editable()
        if args.add_to_requirements:
            setup.add_to_requirements()
        if args.create_example:
            setup.create_example_app()
        if args.create_service_template:
            setup.create_service_template()
        if args.check_installation:
            setup.check_installation()
        if args.run_tests:
            setup.run_tests()

    print("\n🎉 Setup completed!")
    print("Next steps:")
    print("1. Start Redis: redis-server")
    print("2. Run the example: python hotcore_example/main.py")
    print("3. Check the integration guide: integration_guide.md")


if __name__ == "__main__":
    main()
