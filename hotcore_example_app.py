#!/usr/bin/env python3
"""
Example application demonstrating hotcore integration.

This script shows how to use the hotcore module in a Python application
for managing hierarchical data with Redis backend.
"""

import os
import sys
from typing import Any, Dict

# Add the hotcore module to the Python path
# Option 1: If hotcore is installed as a package
try:
    from hotcore import Model
except ImportError:
    # Option 2: If hotcore is in a relative directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "hotcore"))
    from hotcore import Model


class HotcoreExampleApp:
    """Example application using hotcore for data management."""

    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        """Initialize the application with Redis connection."""
        self.model = Model(host=redis_host, port=redis_port)
        self.setup_root_entities()
        self.setup_locations_root()

    def setup_root_entities(self):
        """Set up initial root entities for the application."""
        # Create root container for users
        users_root = self.model.init({})
        users_root["name"] = "Users"
        users_root["type"] = "container"
        users_root["description"] = "Root container for all users"
        self.model.create("root", users_root)
        self.users_root_uuid = users_root["uuid"]

        # Create root container for projects
        projects_root = self.model.init({})
        projects_root["name"] = "Projects"
        projects_root["type"] = "container"
        projects_root["description"] = "Root container for all projects"
        self.model.create("root", projects_root)
        self.projects_root_uuid = projects_root["uuid"]

        print(f"✅ Application initialized with root containers:")
        print(f"   Users: {self.users_root_uuid}")
        print(f"   Projects: {self.projects_root_uuid}")

    def setup_locations_root(self):
        """Set up root container for locations with geospatial support."""
        # Create root container for locations
        locations_root = self.model.init({})
        locations_root["name"] = "Locations"
        locations_root["type"] = "container"
        locations_root["description"] = (
            "Root container for all locations with geospatial support"
        )
        self.model.create("root", locations_root)
        self.locations_root_uuid = locations_root["uuid"]
        print(f"   Locations: {self.locations_root_uuid}")

    def create_user(self, name: str, email: str, role: str = "user") -> Dict[str, Any]:
        """Create a new user entity."""
        user = self.model.init({})
        user["name"] = name
        user["email"] = email
        user["type"] = "user"
        user["role"] = role
        user["status"] = "active"

        created_user = self.model.create(self.users_root_uuid, user)
        print(f"✅ Created user: {name} ({email})")
        return created_user

    def create_project(
        self, name: str, description: str, owner_email: str
    ) -> Dict[str, Any]:
        """Create a new project entity."""
        project = self.model.init({})
        project["name"] = name
        project["description"] = description
        project["type"] = "project"
        project["owner_email"] = owner_email
        project["status"] = "active"

        created_project = self.model.create(self.projects_root_uuid, project)
        print(f"✅ Created project: {name}")
        return created_project

    def find_users_by_role(self, role: str) -> list:
        """Find all users with a specific role."""
        users = list(self.model.find(type="user", role=role))
        print(f"Found {len(users)} users with role '{role}':")
        for user in users:
            print(f"  - {user['name']} ({user['email']})")
        return users

    def find_projects_by_owner(self, owner_email: str) -> list:
        """Find all projects owned by a specific user."""
        projects = list(self.model.find(type="project", owner_email=owner_email))
        print(f"Found {len(projects)} projects owned by {owner_email}:")
        for project in projects:
            print(f"  - {project['name']}: {project['description']}")
        return projects

    def create_location(
        self,
        name: str,
        lat: float,
        lon: float,
        location_type: str = "point",
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a new location entity with geospatial coordinates.

        The location will be automatically added to the geospatial index.
        """
        location = self.model.init({})
        location["name"] = name
        location["type"] = location_type
        location["lat"] = lat
        location["long"] = lon
        location["status"] = "active"

        # Add any additional metadata
        if metadata:
            location.update(metadata)

        created_location = self.model.create(self.locations_root_uuid, location)
        print(f"✅ Created location: {name} at ({lat}, {lon})")
        return created_location

    def search_locations_in_area(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        location_type: str = "office",
    ) -> list:
        """Search for locations of a specific type within a geographic bounding box."""
        locations = self.model.search_bounding_box(
            min_lat, max_lat, min_lon, max_lon, location_type
        )
        print(
            f"Found {len(locations)} {location_type}s in area ({min_lat}, {min_lon}) to ({max_lat}, {max_lon}):"
        )
        for location in locations:
            # Handle entities that might not have all expected fields
            name = location.get("name", "Unknown")
            lat = location.get("lat", "N/A")
            lon = location.get("long", "N/A")
            print(f"  - {name} at ({lat}, {lon})")
        return locations

    def update_location_coordinates(
        self, location_uuid: str, new_lat: float, new_lon: float
    ):
        """Update a location's coordinates.

        The geospatial index will be automatically updated.
        """
        changes = {"uuid": location_uuid, "lat": new_lat, "long": new_lon}
        self.model.apply(changes)
        print(f"✅ Updated location coordinates to ({new_lat}, {new_lon})")

    def update_user_status(self, user_uuid: str, new_status: str):
        """Update a user's status."""
        changes = {"uuid": user_uuid, "status": new_status}
        self.model.apply(changes)
        print(f"✅ Updated user {user_uuid} status to '{new_status}'")

    def get_all_users(self) -> list:
        """Get all users in the system."""
        return list(self.model.find(type="user"))

    def get_all_projects(self) -> list:
        """Get all projects in the system."""
        return list(self.model.find(type="project"))

    def delete_user(self, user_uuid: str):
        """Delete a user from the system."""
        user = self.model.get(user_uuid)
        if user and user.get("type") == "user":
            self.model.delete(user)
            print(f"✅ Deleted user: {user['name']}")
        else:
            print(f"❌ User not found or invalid: {user_uuid}")


def main():
    """Main function demonstrating hotcore usage."""
    print("🚀 Hotcore Example Application")
    print("=" * 40)

    try:
        # Initialize the application
        app = HotcoreExampleApp()

        # Create some sample users
        print("\n📝 Creating sample users...")
        alice = app.create_user("Alice Johnson", "alice@example.com", "admin")
        bob = app.create_user("Bob Smith", "bob@example.com", "user")
        charlie = app.create_user("Charlie Brown", "charlie@example.com", "user")

        # Create some sample projects
        print("\n📝 Creating sample projects...")
        project1 = app.create_project(
            "Web App", "A modern web application", "alice@example.com"
        )
        project2 = app.create_project(
            "Mobile App", "Cross-platform mobile app", "bob@example.com"
        )
        project3 = app.create_project(
            "API Service", "RESTful API service", "alice@example.com"
        )

        # Demonstrate search functionality
        print("\n🔍 Searching for users by role...")
        app.find_users_by_role("admin")
        app.find_users_by_role("user")

        print("\n🔍 Searching for projects by owner...")
        app.find_projects_by_owner("alice@example.com")
        app.find_projects_by_owner("bob@example.com")

        # Demonstrate updates
        print("\n🔄 Updating user status...")
        app.update_user_status(bob["uuid"], "inactive")

        # Demonstrate geospatial functionality
        print("\n🌍 Creating sample locations with coordinates...")
        nyc_office = app.create_location(
            "NYC Office",
            40.7128,
            -74.0060,
            "office",
            {"address": "123 Broadway, NYC", "floor": "10th"},
        )
        la_office = app.create_location(
            "LA Office",
            34.0522,
            -118.2437,
            "office",
            {"address": "456 Sunset Blvd, LA", "floor": "5th"},
        )
        chicago_office = app.create_location(
            "Chicago Office",
            41.8781,
            -87.6298,
            "office",
            {"address": "789 Michigan Ave, Chicago", "floor": "15th"},
        )

        print(
            "\n🔍 Searching for offices in Northeast US (35°N to 45°N, 80°W to 70°W)..."
        )
        northeast_locations = app.search_locations_in_area(
            35.0, 45.0, -80.0, -70.0, "office"
        )

        print("\n🔍 Searching for offices around NYC (40°N to 41°N, 74°W to 73°W)...")
        nyc_area_locations = app.search_locations_in_area(
            40.0, 41.0, -74.0, -73.0, "office"
        )

        print("\n🔄 Updating location coordinates...")
        app.update_location_coordinates(
            nyc_office["uuid"], 40.7589, -73.9851
        )  # Times Square
        print("✅ Moved NYC Office to Times Square")

        # Search again to see the updated location
        print("\n🔍 Searching NYC area again after coordinate update...")
        updated_nyc_locations = app.search_locations_in_area(
            40.0, 41.0, -74.0, -73.0, "office"
        )

        # Show all entities
        print("\n📊 Current system state:")
        users = app.get_all_users()
        projects = app.get_all_projects()
        locations = list(app.model.find(type="office"))
        print(f"Total users: {len(users)}")
        print(f"Total projects: {len(projects)}")
        print(f"Total locations: {len(locations)}")

        print("\n✅ Example application completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure Redis is running: redis-server")
        sys.exit(1)


if __name__ == "__main__":
    main()
