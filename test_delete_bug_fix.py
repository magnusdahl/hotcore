"""
Test to verify the pipeline bug fix in storage.py delete() method.

This test specifically checks that deleting an entity with children works
correctly and doesn't cause memory issues or iterate over pipeline objects.
"""

import pytest
from hotcore import Model


def test_delete_parent_with_multiple_children():
    """
    Test that deleting a parent with many children works correctly.
    
    This test would have failed with the bug (line 275 calling pipe.smembers
    after pipe.multi()) because it would iterate over a pipeline object
    instead of actual child UUIDs.
    """
    # Use localhost for this test
    model = Model("localhost")
    
    try:
        # Clean slate
        model.flush_all()
        
        # Create parent
        parent = model.init({})
        parent["name"] = "Parent Entity"
        parent["type"] = "parent"
        model.create("root", parent)
        parent_uuid = parent["uuid"]
        
        # Create multiple children (enough to catch the bug)
        child_uuids = []
        for i in range(15):
            child = model.init({})
            child["name"] = f"Child {i}"
            child["type"] = "child"
            child["index"] = str(i)
            model.create(parent_uuid, child)
            child_uuids.append(child["uuid"])
        
        # Verify children exist
        children_before = list(model.get_children(parent_uuid))
        assert len(children_before) == 15, f"Expected 15 children, got {len(children_before)}"
        
        # Delete the parent - this is where the bug would manifest
        # With the bug: would iterate over pipeline object, causing massive memory usage
        # With the fix: should correctly reassign children to root
        model.delete(parent)
        
        # Verify parent is deleted
        deleted_parent = model.get(parent_uuid)
        assert deleted_parent == {"uuid": parent_uuid}, "Parent should be deleted"
        
        # Verify children still exist
        for child_uuid in child_uuids:
            child = model.get(child_uuid)
            assert child["uuid"] == child_uuid, f"Child {child_uuid} should still exist"
            assert "name" in child, f"Child {child_uuid} should have its data"
        
        # Verify children were reassigned to root
        for child_uuid in child_uuids:
            parent_of_child = model.get_parent(child_uuid)
            assert parent_of_child["uuid"] == "root", \
                f"Child {child_uuid} should have root as parent after deletion"
        
        print("✅ Test passed! Delete operation with multiple children works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
    finally:
        # Cleanup
        try:
            model.flush_all()
        except:
            pass


def test_delete_parent_with_no_children():
    """Test that deleting a parent with no children works correctly."""
    model = Model("localhost")
    
    try:
        model.flush_all()
        
        # Create parent without children
        parent = model.init({})
        parent["name"] = "Childless Parent"
        model.create("root", parent)
        parent_uuid = parent["uuid"]
        
        # Delete the parent
        model.delete(parent)
        
        # Verify parent is deleted
        deleted_parent = model.get(parent_uuid)
        assert deleted_parent == {"uuid": parent_uuid}, "Parent should be deleted"
        
        print("✅ Test passed! Delete operation with no children works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
    finally:
        try:
            model.flush_all()
        except:
            pass


def test_delete_nested_hierarchy():
    """Test deleting in a nested hierarchy (grandparent > parent > children)."""
    model = Model("localhost")
    
    try:
        model.flush_all()
        
        # Create grandparent
        grandparent = model.init({})
        grandparent["name"] = "Grandparent"
        model.create("root", grandparent)
        
        # Create parent
        parent = model.init({})
        parent["name"] = "Parent"
        model.create(grandparent["uuid"], parent)
        
        # Create children
        for i in range(5):
            child = model.init({})
            child["name"] = f"Child {i}"
            model.create(parent["uuid"], child)
        
        # Delete parent (children should be reassigned to grandparent)
        model.delete(parent)
        
        # Verify parent is deleted
        deleted_parent = model.get(parent["uuid"])
        assert deleted_parent == {"uuid": parent["uuid"]}, "Parent should be deleted"
        
        # Verify children are now under grandparent
        children_of_grandparent = list(model.get_children(grandparent["uuid"]))
        # Should have the 5 children that were reassigned
        child_names = [c["name"] for c in children_of_grandparent if c["name"].startswith("Child")]
        assert len(child_names) == 5, f"Expected 5 reassigned children, got {len(child_names)}"
        
        print("✅ Test passed! Nested hierarchy deletion works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
    finally:
        try:
            model.flush_all()
        except:
            pass


if __name__ == "__main__":
    print("Testing delete operation bug fix...\n")
    
    print("Test 1: Delete parent with multiple children")
    test_delete_parent_with_multiple_children()
    
    print("\nTest 2: Delete parent with no children")
    test_delete_parent_with_no_children()
    
    print("\nTest 3: Delete in nested hierarchy")
    test_delete_nested_hierarchy()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! The bug fix works correctly.")
    print("="*70)

