from unittest import mock
from unittest.mock import patch

from embedchain import App
from embedchain.config import AppConfig
from embedchain.embedder.base import BaseEmbedder
from embedchain.vectordb.pinecone import PineconeDB
from embedchain.config.vectordb.pinecone import PineconeDBConfig


class TestPinecone:
    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_init(self, pinecone_mock):
        """Test that the PineconeDB can be initialized."""
        # Create a PineconeDB instance
        PineconeDB()

        # Assert that the Pinecone client was initialized
        pinecone_mock.init.assert_called_once()
        pinecone_mock.list_indexes.assert_called_once()
        pinecone_mock.Index.assert_called_once()

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_set_embedder(self, pinecone_mock):
        """Test that the embedder can be set."""

        # Set the embedder
        embedder = BaseEmbedder()

        # Create a PineconeDB instance
        db = PineconeDB()
        app_config = AppConfig(collect_metrics=False)
        App(config=app_config, db=db, embedding_model=embedder)

        # Assert that the embedder was set
        assert db.embedder == embedder
        pinecone_mock.init.assert_called_once()

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_add_documents(self, pinecone_mock):
        """Test that documents can be added to the database."""
        pinecone_client_mock = pinecone_mock.Index.return_value

        embedding_function = mock.Mock()
        base_embedder = BaseEmbedder()
        base_embedder.set_embedding_fn(embedding_function)
        embedding_function.return_value = [[0, 0, 0], [1, 1, 1]]

        # Create a PineconeDb instance
        db = PineconeDB()
        app_config = AppConfig(collect_metrics=False)
        App(config=app_config, db=db, embedding_model=base_embedder)

        # Add some documents to the database
        documents = ["This is a document.", "This is another document."]
        metadatas = [{}, {}]
        ids = ["doc1", "doc2"]
        db.add(documents, metadatas, ids)

        expected_pinecone_upsert_args = [
            {"id": "doc1", "values": [0, 0, 0], "metadata": {"text": "This is a document."}},
            {"id": "doc2", "values": [1, 1, 1], "metadata": {"text": "This is another document."}},
        ]
        # Assert that the Pinecone client was called to upsert the documents
        pinecone_client_mock.upsert.assert_called_once_with(tuple(expected_pinecone_upsert_args))

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_query_documents(self, pinecone_mock):
        """Test that documents can be queried from the database."""
        pinecone_client_mock = pinecone_mock.Index.return_value

        embedding_function = mock.Mock()
        base_embedder = BaseEmbedder()
        base_embedder.set_embedding_fn(embedding_function)
        vectors = [[0, 0, 0]]
        embedding_function.return_value = vectors
        # Create a PineconeDB instance
        db = PineconeDB()
        app_config = AppConfig(collect_metrics=False)
        App(config=app_config, db=db, embedding_model=base_embedder)

        # Query the database for documents that are similar to "document"
        input_query = ["document"]
        n_results = 1
        db.query(input_query, n_results, where={})

        # Assert that the Pinecone client was called to query the database
        pinecone_client_mock.query.assert_called_once_with(
            vector=db.embedder.embedding_fn(input_query)[0], top_k=n_results, filter={}, include_metadata=True
        )

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_reset(self, pinecone_mock):
        """Test that the database can be reset."""
        # Create a PineconeDb instance
        db = PineconeDB()
        app_config = AppConfig(collect_metrics=False)
        App(config=app_config, db=db, embedding_model=BaseEmbedder())

        # Reset the database
        db.reset()

        # Assert that the Pinecone client was called to delete the index
        pinecone_mock.delete_index.assert_called_once_with(db.config.index_name)

        # Assert that the index is recreated
        pinecone_mock.Index.assert_called_with(db.config.index_name)

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_custom_index_name_if_it_exists(self, pinecone_mock):
        """Tests custom index name is used if it exists"""
        pinecone_mock.list_indexes.return_value = ["custom_index_name"]
        db_config = PineconeDBConfig(index_name="custom_index_name")
        _ = PineconeDB(config=db_config)

        pinecone_mock.list_indexes.assert_called_once()
        pinecone_mock.create_index.assert_not_called()
        pinecone_mock.Index.assert_called_with("custom_index_name")

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_custom_index_name_creation(self, pinecone_mock):
        """Test custom index name is created if it doesn't exists already"""
        pinecone_mock.list_indexes.return_value = []
        db_config = PineconeDBConfig(index_name="custom_index_name")
        _ = PineconeDB(config=db_config)

        pinecone_mock.list_indexes.assert_called_once()
        pinecone_mock.create_index.assert_called_once()
        pinecone_mock.Index.assert_called_with("custom_index_name")

    @patch("embedchain.vectordb.pinecone.pinecone")
    def test_default_index_name_is_used(self, pinecone_mock):
        """Test default index name is used if custom index name is not provided"""
        db_config = PineconeDBConfig(collection_name="my-collection")
        _ = PineconeDB(config=db_config)

        pinecone_mock.list_indexes.assert_called_once()
        pinecone_mock.create_index.assert_called_once()
        pinecone_mock.Index.assert_called_with(f"{db_config.collection_name}-{db_config.vector_dimension}")
