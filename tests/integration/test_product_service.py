"""Integration tests for ProductService with SQLSpec."""

import pytest

from app.services.product import ProductService

pytestmark = pytest.mark.anyio


class TestProductService:
    """Test suite for ProductService using SQLSpec driver patterns."""

    async def test_get_all_products(
        self,
        product_service: ProductService,
    ) -> None:
        """Test retrieving all products."""
        products = await product_service.get_all()

        assert isinstance(products, list)
        # Should have at least some products from seed data
        assert len(products) >= 0

        if products:
            # Verify Product schema attributes
            product = products[0]
            assert product.id is not None
            assert product.name is not None
            assert product.price is not None
            assert product.description is not None

    async def test_get_by_id(
        self,
        product_service: ProductService,
    ) -> None:
        """Test retrieving product by ID."""
        # Get all products first
        products = await product_service.get_all()

        if products:
            product_id = products[0].id
            product = await product_service.get_by_id(product_id)

            assert product is not None
            assert product.id == product_id
            assert product.name is not None

    async def test_get_by_id_not_found(
        self,
        product_service: ProductService,
    ) -> None:
        """Test retrieving non-existent product returns None."""
        product = await product_service.get_by_id(99999999)
        assert product is None

    async def test_search_by_description(
        self,
        product_service: ProductService,
    ) -> None:
        """Test text-based description search."""
        # Search for common coffee terms
        results = await product_service.search_by_description("coffee")

        assert isinstance(results, list)
        # Verify all results contain the search term
        for result in results:
            assert "coffee" in result.description.lower()

    async def test_get_products_without_embeddings(
        self,
        product_service: ProductService,
    ) -> None:
        """Test pagination of products without embeddings."""
        products, total_count = await product_service.get_products_without_embeddings(
            limit=10, offset=0
        )

        assert isinstance(products, list)
        assert isinstance(total_count, int)
        assert total_count >= 0
        assert len(products) <= 10

        # Verify all results have null embeddings
        for product in products:
            assert product.embedding is None

    async def test_vector_search(
        self,
        product_service: ProductService,
    ) -> None:
        """Test vector similarity search with Oracle VECTOR_DISTANCE."""
        # Create a mock embedding (768 dimensions)
        query_embedding = [0.1] * 768

        results = await product_service.search_by_vector(
            query_embedding=query_embedding,
            limit=5,
            similarity_threshold=0.3,
        )

        assert isinstance(results, list)
        assert len(results) <= 5

        # Verify SQLSpec automatically handles vector conversion
        for result in results:
            assert "similarity_score" in result
            assert 0.0 <= result["similarity_score"] <= 1.0
            # Results should be sorted by similarity (highest first)

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]

    async def test_update_embedding(
        self,
        product_service: ProductService,
    ) -> None:
        """Test updating product embedding with automatic vector conversion."""
        # Get a product
        products = await product_service.get_all()
        if not products:
            pytest.skip("No products available for testing")

        product_id = products[0].id

        # Create a test embedding (768 dimensions)
        test_embedding = [0.5] * 768

        # Update embedding - SQLSpec should handle vector conversion automatically
        success = await product_service.update_embedding(product_id, test_embedding)
        assert success is True

        # Verify the embedding was updated
        updated_product = await product_service.get_by_id(product_id)
        assert updated_product is not None
        assert updated_product.embedding is not None
        assert updated_product.updated_at is not None

    async def test_create_product_with_returning(
        self,
        product_service: ProductService,
    ) -> None:
        """Test creating product with RETURNING clause."""
        # Create a new product with embedding
        test_embedding = [0.1] * 768

        new_product = await product_service.create_product(
            name="Test Coffee SQLSpec",
            price=12.99,
            description="A test coffee for SQLSpec validation",
            category="Coffee",
            sku="TEST-SKU-001",
            in_stock=True,
            embedding=test_embedding,
        )

        assert new_product is not None
        assert new_product.id is not None
        assert new_product.name == "Test Coffee SQLSpec"
        assert new_product.price == 12.99
        assert new_product.embedding is not None

    async def test_update_product(
        self,
        product_service: ProductService,
    ) -> None:
        """Test updating product fields."""
        products = await product_service.get_all()
        if not products:
            pytest.skip("No products available for testing")

        product_id = products[0].id
        original_name = products[0].name

        # Update product
        updated = await product_service.update_product(
            product_id=product_id,
            updates={"name": "Updated Name", "price": 99.99},
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.price == 99.99

        # Restore original name
        await product_service.update_product(
            product_id=product_id,
            updates={"name": original_name},
        )
