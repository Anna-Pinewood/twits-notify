import pytest
from unittest.mock import MagicMock
import litellm
import pytest_mock


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    response = {
        'choices': [{
            'message': {
                'content': '''{
                    "tags": ["python", "programming", "development"],
                    "discussion_summary": "A discussion about Python programming techniques."
                }'''
            }
        }],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }
    return response


@pytest.fixture
def mock_llm_interface(mocker, mock_llm_response):
    """Create a mock LLM interface."""
    mock_completion = mocker.patch('litellm.completion')
    mock_completion.return_value = mock_llm_response

    mock_cost = mocker.patch('litellm.completion_cost')
    mock_cost.return_value = 0.02

    return {
        'completion': mock_completion,
        'cost': mock_cost,
        'response': mock_llm_response
    }


@pytest.fixture
def sample_prompt_params():
    """Sample parameters for LLM prompt formatting."""
    return {
        'title': 'Test Post',
        'content': 'This is a test post content',
        'subreddit': 'testsubreddit'
    }
