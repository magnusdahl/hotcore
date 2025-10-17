import uuid

import pytest

from hotcore import Model


class TestIntegration:
    """Integration tests for the hotcore package.

    These tests can run against either fakeredis or a real Redis instance
    depending on the USE_REAL_REDIS environment variable.
    """

    def test_complete_workflow(self, model):
        """Test a complete workflow with the model."""
        # Create a root entity
        root = model.init({})
        root["name"] = "Organization"
        root["type"] = "org"
        model.create("root", root)

        # Create departments
        engineering = model.init({})
        engineering["name"] = "Engineering"
        engineering["type"] = "department"
        engineering["code"] = "ENG"
        model.create(root["uuid"], engineering)

        marketing = model.init({})
        marketing["name"] = "Marketing"
        marketing["type"] = "department"
        marketing["code"] = "MKT"
        model.create(root["uuid"], marketing)

        # Create employees in departments
        for i, dept in enumerate([engineering, marketing]):
            for j in range(3):  # 3 employees per department
                employee = model.init({})
                employee["name"] = f"Employee {i}-{j}"
                employee["type"] = "employee"
                employee["email"] = f"employee{i}{j}@example.com"
                employee["department"] = dept["code"]
                employee["status"] = "active" if j != 1 else "inactive"
                model.create(dept["uuid"], employee)

        # Test hierarchy navigation
        # Get all departments
        departments = list(model.get_children(root["uuid"]))
        assert len(departments) == 2

        # Get all employees
        all_employees = []
        for dept in departments:
            employees = list(model.get_children(dept["uuid"]))
            all_employees.extend(employees)
        assert len(all_employees) == 6

        # Test search functionality
        # Find by department code
        eng_employees = list(model.find(department="ENG"))
        assert len(eng_employees) == 3

        # Find by status
        active_employees = list(model.find(type="employee", status="active"))
        assert len(active_employees) == 4  # 2 per department

        # Find by email pattern
        dept0_employees = list(model.find(email="employee0*"))
        assert len(dept0_employees) == 3

        # Test parent lookup
        random_employee = eng_employees[0]
        parent_dept = model.get_parent(random_employee["uuid"])
        assert parent_dept["uuid"] == engineering["uuid"]

        # Test making changes
        # Deactivate a department
        changes = {"uuid": marketing["uuid"], "status": "inactive"}
        model.apply(changes)

        # Verify the change
        updated_marketing = model.get(marketing["uuid"])
        assert updated_marketing["status"] == "inactive"

        # Test deletion
        # Delete an employee
        employee_to_delete = eng_employees[0]
        model.delete(employee_to_delete)

        # Verify the employee is gone
        empty_entity = model.get(employee_to_delete["uuid"])
        assert empty_entity == {"uuid": employee_to_delete["uuid"]}

        # Verify department still has remaining employees
        remaining_employees = list(model.get_children(engineering["uuid"]))
        assert len(remaining_employees) == 2

    def test_concurrent_operations(self, model):
        """Test operations that would normally be concurrent."""
        # Create an entity
        entity = model.init({})
        entity["name"] = "Shared Entity"
        entity["type"] = "shared"
        entity["counter"] = "0"
        parent_uuid = "root"

        model.create(parent_uuid, entity)

        # Simulate multiple updates
        # In a real app, these would be from different processes/threads
        for i in range(1, 4):
            # Get the current value
            current = model.get(entity["uuid"])
            current_counter = int(current["counter"])

            # Update the counter
            changes = {"uuid": entity["uuid"], "counter": str(current_counter + 1)}
            model.apply(changes)

        # Verify the final value
        final = model.get(entity["uuid"])
        assert final["counter"] == "3"

    def test_large_dataset(self, model):
        """Test operations on a larger dataset."""
        # Create a parent
        parent = model.init({})
        parent["name"] = "Parent"
        parent["type"] = "container"
        model.create("root", parent)

        # Create many child entities with various attributes
        for i in range(20):
            child = model.init({})
            child["name"] = f"Item {i}"
            child["type"] = "item"
            child["category"] = f"cat-{i % 5}"  # 5 different categories
            child["status"] = "active" if i % 3 != 0 else "inactive"
            child["priority"] = "high" if i < 5 else ("medium" if i < 15 else "low")
            child["tags"] = f"tag{i % 4},common"  # Some common tags
            model.create(parent["uuid"], child)

        # Test complex searches
        # Find active items with high priority
        results = list(model.find(type="item", status="active", priority="high"))
        assert len(results) > 0  # Should have some matches
        assert all(
            item["status"] == "active" and item["priority"] == "high"
            for item in results
        )

        # Find items in category 2
        cat2_items = list(model.find(category="cat-2"))
        assert len(cat2_items) == 4  # Should be 4 items (20/5)

        # Find items with a specific tag
        tag1_items = list(model.find(tags="*tag1*"))
        assert len(tag1_items) == 5  # 20/4 items have tag1
