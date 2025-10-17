"""Unit tests for hotcore geospatial functionality."""

from unittest.mock import Mock, patch

import pytest
import redis

from hotcore import GeospatialManager, Model, RedisConnectionManager


class TestGeospatialManager:
    """Test the GeospatialManager class in isolation."""

    @pytest.fixture
    def connection_manager(self):
        """Create a mock connection manager."""
        return Mock(spec=RedisConnectionManager)

    @pytest.fixture
    def geospatial_manager(self, connection_manager):
        """Create a GeospatialManager instance."""
        return GeospatialManager(connection_manager)

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = Mock()
        client.geoadd.return_value = 1
        client.zrem.return_value = 1
        # GEORADIUS returns (member, coordinates) when withcoord=True (no distance)
        # Use coordinates that fall within the test bounding box (40.0-41.0 lat, -74.0 to -73.0 lon)
        client.georadius.return_value = [
            ("entity1", (-73.9857, 40.7484)),  # Within bounding box
            ("entity2", (-73.9950, 40.7500)),  # Within bounding box
        ]
        return client

    def test_has_coordinates_valid(self, geospatial_manager):
        """Test _has_coordinates with valid coordinates."""
        entity = {"lat": 40.7128, "long": -74.0060}
        assert geospatial_manager._has_coordinates(entity) is True

    def test_has_coordinates_missing_lat(self, geospatial_manager):
        """Test _has_coordinates with missing latitude."""
        entity = {"long": -74.0060}
        assert geospatial_manager._has_coordinates(entity) is False

    def test_has_coordinates_missing_long(self, geospatial_manager):
        """Test _has_coordinates with missing longitude."""
        entity = {"lat": 40.7128}
        assert geospatial_manager._has_coordinates(entity) is False

    def test_has_coordinates_none_values(self, geospatial_manager):
        """Test _has_coordinates with None values."""
        entity = {"lat": None, "long": -74.0060}
        assert geospatial_manager._has_coordinates(entity) is False

        entity = {"lat": 40.7128, "long": None}
        assert geospatial_manager._has_coordinates(entity) is False

    def test_has_coordinates_wrong_types(self, geospatial_manager):
        """Test _has_coordinates with wrong data types."""
        entity = {"lat": "40.7128", "long": -74.0060}
        assert geospatial_manager._has_coordinates(entity) is False

        entity = {"lat": 40.7128, "long": "-74.0060"}
        assert geospatial_manager._has_coordinates(entity) is False

    def test_validate_coordinates_valid(self, geospatial_manager):
        """Test _validate_coordinates with valid coordinates."""
        # Should not raise any exception
        geospatial_manager._validate_coordinates(40.7128, -74.0060)
        geospatial_manager._validate_coordinates(0.0, 0.0)
        geospatial_manager._validate_coordinates(-90.0, -180.0)
        geospatial_manager._validate_coordinates(90.0, 180.0)

    def test_validate_coordinates_invalid_latitude(self, geospatial_manager):
        """Test _validate_coordinates with invalid latitude."""
        with pytest.raises(
            ValueError, match="Latitude must be between -90 and 90 degrees"
        ):
            geospatial_manager._validate_coordinates(91.0, -74.0060)

        with pytest.raises(
            ValueError, match="Latitude must be between -90 and 90 degrees"
        ):
            geospatial_manager._validate_coordinates(-91.0, -74.0060)

    def test_validate_coordinates_invalid_longitude(self, geospatial_manager):
        """Test _validate_coordinates with invalid longitude."""
        with pytest.raises(
            ValueError, match="Longitude must be between -180 and 180 degrees"
        ):
            geospatial_manager._validate_coordinates(40.7128, 181.0)

        with pytest.raises(
            ValueError, match="Longitude must be between -180 and 180 degrees"
        ):
            geospatial_manager._validate_coordinates(40.7128, -181.0)

    def test_add_to_index_with_coordinates(
        self, geospatial_manager, connection_manager, mock_redis_client
    ):
        """Test add_to_index with valid coordinates."""
        connection_manager.get_client.return_value = mock_redis_client
        connection_manager.get_geospatial_key.return_value = "geo:user"

        entity = {"lat": 40.7128, "long": -74.0060, "type": "user"}
        geospatial_manager.add_to_index("entity123", entity)

        # Verify Redis client was called correctly
        mock_redis_client.geoadd.assert_called_once_with(
            "geo:user", [-74.0060, 40.7128, "entity123"]
        )

    def test_add_to_index_without_coordinates(
        self, geospatial_manager, connection_manager, mock_redis_client
    ):
        """Test add_to_index without coordinates."""
        connection_manager.get_client.return_value = mock_redis_client

        entity = {"name": "test", "type": "user"}
        geospatial_manager.add_to_index("entity123", entity)

        # Verify Redis client was not called
        mock_redis_client.geoadd.assert_not_called()

    def test_add_to_index_invalid_coordinates(
        self, geospatial_manager, connection_manager, mock_redis_client
    ):
        """Test add_to_index with invalid coordinates."""
        connection_manager.get_client.return_value = mock_redis_client

        entity = {"lat": 91.0, "long": -74.0060}  # Invalid latitude

        with pytest.raises(
            ValueError, match="Latitude must be between -90 and 90 degrees"
        ):
            geospatial_manager.add_to_index("entity123", entity)

    def test_remove_from_index(
        self, geospatial_manager, connection_manager, mock_redis_client
    ):
        """Test remove_from_index."""
        connection_manager.get_client.return_value = mock_redis_client
        connection_manager.get_geospatial_key.return_value = "geo:user"

        entity = {"type": "user"}
        geospatial_manager.remove_from_index("entity123", entity)

        # Verify Redis client was called correctly
        mock_redis_client.zrem.assert_called_once_with("geo:user", "entity123")

    def test_search_bounding_box_valid(
        self, geospatial_manager, connection_manager, mock_redis_client
    ):
        """Test search_bounding_box with valid parameters."""
        connection_manager.get_client.return_value = mock_redis_client
        connection_manager.get_geospatial_key.return_value = "geo:user"

        # Mock the execute_command to return a list of results
        # Coordinates should be within the bounding box (40.0, 41.0, -74.0, -73.0)
        # Redis returns coordinates as strings in (lon, lat) order
        mock_redis_client.execute_command.return_value = [
            (
                "entity1",
                ("-73.5", "40.5"),
            ),  # lon=-73.5 (within -74.0 to -73.0), lat=40.5 (within 40.0-41.0)
            (
                "entity2",
                ("-73.2", "40.8"),
            ),  # lon=-73.2 (within -74.0 to -73.0), lat=40.8 (within 40.0-41.0)
        ]

        results = geospatial_manager.search_bounding_box(
            40.0, 41.0, -74.0, -73.0, "user"
        )

        # Verify Redis client was called
        mock_redis_client.execute_command.assert_called_once()
        assert len(results) == 2
        assert "entity1" in results
        assert "entity2" in results

    def test_search_bounding_box_invalid_latitude_bounds(self, geospatial_manager):
        """Test search_bounding_box with invalid latitude bounds."""
        with pytest.raises(
            ValueError, match="Latitude bounds must be between -90 and 90 degrees"
        ):
            geospatial_manager.search_bounding_box(
                45.0, 35.0, -74.0, -73.0
            )  # min > max

    def test_search_bounding_box_invalid_longitude_bounds(self, geospatial_manager):
        """Test search_bounding_box with invalid longitude bounds."""
        with pytest.raises(
            ValueError, match="Longitude bounds must be between -180 and 180 degrees"
        ):
            geospatial_manager.search_bounding_box(
                40.0, 41.0, -70.0, -80.0
            )  # min > max

    def test_search_bounding_box_out_of_range(self, geospatial_manager):
        """Test search_bounding_box with out-of-range coordinates."""
        with pytest.raises(
            ValueError, match="Latitude bounds must be between -90 and 90 degrees"
        ):
            geospatial_manager.search_bounding_box(91.0, 92.0, -74.0, -73.0)

        with pytest.raises(
            ValueError, match="Longitude bounds must be between -180 and 180 degrees"
        ):
            geospatial_manager.search_bounding_box(40.0, 41.0, -181.0, -180.0)


class TestModelGeospatialIntegration:
    """Test geospatial functionality integrated with the Model class."""

    @pytest.fixture
    def entity_with_coordinates(self):
        """Create an entity with valid coordinates."""
        return {"name": "Test User", "type": "user", "lat": 40.7128, "long": -74.0060}

    @pytest.fixture
    def entity_without_coordinates(self):
        """Create an entity without coordinates."""
        return {"name": "Test Entity", "type": "virtual"}

    def test_create_entity_with_coordinates(self, model, entity_with_coordinates):
        """Test that entities with coordinates are automatically indexed."""
        # Mock the geospatial manager to verify it's called
        with patch.object(model.geospatial, "add_to_index") as mock_add:
            # Use model.init to generate UUID
            entity = model.init(entity_with_coordinates)
            created_entity = model.create("root", entity)

            # Verify the entity was created
            assert created_entity["uuid"] == entity["uuid"]

            # Verify geospatial indexing was attempted
            # The entity may have h3_r6 field added by h3_index.prepare_entity if h3 is available
            mock_add.assert_called_once()
            call_args = mock_add.call_args[0]
            assert call_args[0] == created_entity["uuid"]  # entity_uuid
            # The entity should contain the original fields plus potentially h3_r6
            entity_arg = call_args[1]
            assert entity_arg["name"] == "Test User"
            assert entity_arg["type"] == "user"
            assert entity_arg["lat"] == 40.7128
            assert entity_arg["long"] == -74.006
            assert entity_arg["uuid"] == created_entity["uuid"]

    def test_create_entity_without_coordinates(self, model, entity_without_coordinates):
        """Test that entities without coordinates are not indexed."""
        # Mock the geospatial manager's _has_coordinates method to return False
        with patch.object(model.geospatial, "_has_coordinates", return_value=False):
            # Use model.init to generate UUID
            entity = model.init(entity_without_coordinates)
            created_entity = model.create("root", entity)

            # Verify the entity was created
            assert created_entity["uuid"] == entity["uuid"]

            # Since _has_coordinates returns False, add_to_index should return early
            # and not make any Redis calls

    def test_update_entity_coordinates(self, model, entity_with_coordinates):
        """Test that coordinate updates are automatically indexed."""
        # First create the entity
        entity = model.init(entity_with_coordinates)
        created_entity = model.create("root", entity)

        # Mock the storage to return the updated entity with new coordinates
        updated_entity = created_entity.copy()
        updated_entity.update(
            {"lat": 42.3601, "long": -71.0589}  # New latitude  # New longitude
        )

        with patch.object(model.storage, "get", return_value=updated_entity):
            # Mock the geospatial manager for the update
            with patch.object(model.geospatial, "add_to_index") as mock_add:
                # Update coordinates
                changes = {
                    "uuid": created_entity["uuid"],
                    "lat": 42.3601,  # New latitude
                    "long": -71.0589,  # New longitude
                }
                model.apply(changes)

                # Verify geospatial indexing was attempted
                mock_add.assert_called_once_with(created_entity["uuid"], updated_entity)

    def test_update_entity_non_coordinates(self, model, entity_with_coordinates):
        """Test that non-coordinate updates don't trigger geospatial indexing."""
        # First create the entity
        entity = model.init(entity_with_coordinates)
        created_entity = model.create("root", entity)

        # Mock the geospatial manager for the update
        with patch.object(model.geospatial, "add_to_index") as mock_add:
            # Update non-coordinate attributes
            changes = {"uuid": created_entity["uuid"], "name": "Updated Name"}
            model.apply(changes)

            # Verify geospatial indexing was not attempted
            mock_add.assert_not_called()

    def test_delete_entity_with_coordinates(self, model, entity_with_coordinates):
        """Test that entities are removed from geospatial index when deleted."""
        # First create the entity
        entity = model.init(entity_with_coordinates)
        created_entity = model.create("root", entity)

        # Mock the geospatial manager for deletion
        with patch.object(model.geospatial, "remove_from_index") as mock_remove:
            # Delete the entity
            model.delete(created_entity)

            # Verify geospatial removal was attempted
            mock_remove.assert_called_once_with(created_entity["uuid"], created_entity)

    def test_search_bounding_box_integration(self, model):
        """Test the search_bounding_box method integration."""
        # Mock the geospatial manager's search method
        with patch.object(model.geospatial, "search_bounding_box") as mock_search:
            mock_search.return_value = ["entity1", "entity2"]

            # Mock the storage get method to return fake entities
            with patch.object(model.storage, "get") as mock_get:
                mock_get.side_effect = [
                    {"uuid": "entity1", "name": "Entity 1", "lat": 40.0, "long": -74.0},
                    {"uuid": "entity2", "name": "Entity 2", "lat": 40.5, "long": -73.5},
                ]

                # Perform the search
                results = model.search_bounding_box(40.0, 41.0, -74.0, -73.0, "user")

                # Verify the search was performed
                mock_search.assert_called_once_with(40.0, 41.0, -74.0, -73.0, "user")

                # Verify results were retrieved
                assert len(results) == 2
                assert results[0]["name"] == "Entity 1"
                assert results[1]["name"] == "Entity 2"

    def test_search_bounding_box_validation(self, model):
        """Test that search_bounding_box validates input parameters."""
        # Test invalid latitude bounds
        with pytest.raises(
            ValueError, match="Latitude bounds must be between -90 and 90 degrees"
        ):
            model.search_bounding_box(45.0, 35.0, -74.0, -73.0)

        # Test invalid longitude bounds
        with pytest.raises(
            ValueError, match="Longitude bounds must be between -180 and 180 degrees"
        ):
            model.search_bounding_box(40.0, 41.0, -70.0, -80.0)

    def test_search_bounding_box_error_handling(self, model):
        """Test error handling in search_bounding_box."""
        # Mock the geospatial manager to raise an error
        with patch.object(model.geospatial, "search_bounding_box") as mock_search:
            mock_search.side_effect = Exception("Redis error")

            with pytest.raises(Exception, match="Redis error"):
                model.search_bounding_box(40.0, 41.0, -74.0, -73.0)


class TestGeospatialEdgeCases:
    """Test edge cases and error conditions."""

    def test_coordinate_precision(self, model):
        """Test that coordinates with high precision are handled correctly."""
        entity = model.init(
            {
                "name": "Precise Location",
                "type": "landmark",
                "lat": 40.712800000000001,  # High precision
                "long": -74.006000000000001,
            }
        )

        # Should not raise any validation errors
        assert entity["lat"] == 40.712800000000001
        assert entity["long"] == -74.006000000000001

    def test_coordinate_boundary_values(self, model):
        """Test coordinate boundary values."""
        # Test exact boundary values
        entity = model.init(
            {
                "name": "Boundary Test",
                "type": "test",
                "lat": 90.0,  # Maximum latitude
                "long": 180.0,  # Maximum longitude
            }
        )

        # Should be valid
        assert entity["lat"] == 90.0
        assert entity["long"] == 180.0

        # Test negative boundary values
        entity = model.init(
            {
                "name": "Negative Boundary Test",
                "type": "test",
                "lat": -90.0,  # Minimum latitude
                "long": -180.0,  # Minimum longitude
            }
        )

        # Should be valid
        assert entity["lat"] == -90.0
        assert entity["long"] == -180.0

    def test_empty_bounding_box(self, model):
        """Test bounding box with minimal area."""
        # Mock the geospatial manager to return a known result
        with patch.object(model.geospatial, "search_bounding_box") as mock_search:
            mock_search.return_value = ["tiny_box_uuid"]

            # Mock the storage get method
            with patch.object(model.storage, "get") as mock_get:
                mock_get.return_value = {
                    "uuid": "tiny_box_uuid",
                    "name": "Tiny Box Test",
                    "type": "test",
                    "lat": 40.0,
                    "long": -74.0,
                }

                # Search in a tiny area around the point
                results = model.search_bounding_box(
                    39.999, 40.001, -74.001, -73.999, "test"
                )

                # Should find the entity
                assert len(results) == 1
                assert results[0]["name"] == "Tiny Box Test"

    def test_large_bounding_box(self, model):
        """Test bounding box covering a large area."""
        # Mock the geospatial manager to return known results
        with patch.object(model.geospatial, "search_bounding_box") as mock_search:
            mock_search.return_value = ["nyc_uuid", "la_uuid", "chicago_uuid"]

            # Mock the storage get method to return different entities
            with patch.object(model.storage, "get") as mock_get:
                mock_get.side_effect = [
                    {
                        "uuid": "nyc_uuid",
                        "name": "NYC",
                        "type": "city",
                        "lat": 40.7128,
                        "long": -74.0060,
                    },
                    {
                        "uuid": "la_uuid",
                        "name": "LA",
                        "type": "city",
                        "lat": 34.0522,
                        "long": -118.2437,
                    },
                    {
                        "uuid": "chicago_uuid",
                        "name": "Chicago",
                        "type": "city",
                        "lat": 41.8781,
                        "long": -87.6298,
                    },
                ]

                # Search in a large area covering all entities
                results = model.search_bounding_box(30.0, 45.0, -120.0, -70.0, "city")

                # Should find all entities
                assert len(results) == 3
                names = [entity["name"] for entity in results]
                assert "NYC" in names
                assert "LA" in names
                assert "Chicago" in names
