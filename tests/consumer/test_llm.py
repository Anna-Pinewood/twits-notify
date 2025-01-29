import pytest
import json
from backend.consumer.llm import LLMInterface

def test_llm_interface_init():
    """Test LLM interface initialization."""
    llm = LLMInterface(
        model_name="test-model",
        llm_api_key="test-key",
        llm_base_url="http://test-url",
        prompt="test prompt"
    )
    
    assert llm.model_name == "test-model"
    assert llm.llm_api_key == "test-key"
    assert llm.llm_base_url == "http://test-url"
    assert llm.prompt == "test prompt"

def test_llm_interface_send_request(mock_llm_interface, sample_prompt_params):
    """Test sending request to LLM."""
    llm = LLMInterface(prompt="Test prompt with {title} and {content}")
    
    response = llm.send_request(call_params=sample_prompt_params)
    
    assert response == mock_llm_interface['response']
    mock_llm_interface['completion'].assert_called_once()
    mock_llm_interface['cost'].assert_called_once()

def test_get_response_content(mock_llm_response):
    """Test parsing LLM response content."""
    result = LLMInterface.get_response_content(mock_llm_response)
    
    assert isinstance(result, dict)
    assert 'tags' in result
    assert 'discussion_summary' in result

def test_get_response_content_raw_text(mock_llm_response):
    """Test parsing LLM response when it's not JSON."""
    mock_llm_response['choices'][0]['message']['content'] = "Plain text response"
    
    result = LLMInterface.get_response_content(mock_llm_response)
    
    assert isinstance(result, str)
    assert result == "Plain text response"

def test_null_base_url():
    """Test initialization with null base URL."""
    llm = LLMInterface(llm_base_url="null")
    assert llm.llm_base_url is None
