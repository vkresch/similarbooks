import pytest
import numpy as np
from scipy.sparse import csr_matrix
from pathlib import Path
from unittest.mock import patch, MagicMock

from som.utils import (
    process_documents,
    process_batch,
)


# Create a fixture for test documents
@pytest.fixture
def test_documents():
    return [
        "This is the first document.",
        "This document is the second document.",
        "And this is the third one.",
        "Is this the first document?",
    ]


# Mock the load_documents_list function
@pytest.fixture
def mock_load_documents(test_documents):
    with patch("som.utils.load_documents_list") as mock:
        mock.return_value = test_documents
        yield mock


def test_process_documents(mock_load_documents, test_documents):
    # Set up test parameters
    test_directory = Path("/test/data")
    ngram_range = (1, 1)
    min_df = 1

    # Call the function
    dtm, feature_names = process_documents(test_directory, ngram_range, min_df)

    # Check that load_documents_list was called with the correct argument
    mock_load_documents.assert_called_once_with(test_directory)

    # Check the shape of the DTM
    assert dtm.shape == (4, 9)  # 4 documents, 9 unique words

    # Check that the DTM is a CSR matrix
    assert isinstance(dtm, csr_matrix)

    # Check the feature names
    expected_features = [
        "and",
        "document",
        "first",
        "is",
        "one",
        "second",
        "the",
        "third",
        "this",
    ]
    assert list(feature_names) == expected_features

    # Check the content of the DTM
    expected_dtm = np.array(
        [
            [0, 1, 1, 1, 0, 0, 1, 0, 1],
            [0, 2, 0, 1, 0, 1, 1, 0, 1],
            [1, 0, 0, 1, 1, 0, 1, 1, 1],
            [0, 1, 1, 1, 0, 0, 1, 0, 1],
        ]
    )
    assert np.array_equal(dtm.toarray(), expected_dtm)


def test_process_documents_bigrams(mock_load_documents, test_documents):
    # Set up test parameters
    test_directory = Path("/test/data")
    ngram_range = (2, 2)
    min_df = 1

    # Call the function
    dtm, feature_names = process_documents(test_directory, ngram_range, min_df)

    # Check the shape of the DTM (number of bigrams will be different)
    assert dtm.shape[0] == 4  # 4 documents

    # Check that the DTM is a CSR matrix
    assert isinstance(dtm, csr_matrix)

    # Check some expected bigrams
    expected_bigrams = ["is the", "the first", "the second", "this is"]
    for bigram in expected_bigrams:
        assert bigram in feature_names


def test_process_documents_empty(mock_load_documents):
    # Mock an empty document list
    mock_load_documents.return_value = []

    # Set up test parameters
    test_directory = Path("/test/data")
    ngram_range = (1, 1)
    min_df = 1

    # Call the function
    dtm, feature_names = process_documents(test_directory, ngram_range, min_df)

    # Check that the DTM is empty
    assert dtm.shape == (0, 0)
    assert len(feature_names) == 0
