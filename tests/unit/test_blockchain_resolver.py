"""
Unit tests for BlockchainResolver class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import subprocess
import json
import tempfile
import os

from src.blockchain_resolver import BlockchainResolver
from src.resolution_researcher import ResolutionResult
from src.market_monitor import MarketStatus


class TestBlockchainResolver:
    """Tests for BlockchainResolver class"""
    
    @patch('src.blockchain_resolver.Config')
    def test_init(self, mock_config):
        """Test BlockchainResolver initialization"""
        mock_config.POETRY_PATH = "poetry"
        mock_config.OMEN_SCRIPT_PROJECT_PATH = "/path/to/omen"
        mock_config.OMEN_PRIVATE_KEY = "0x123"
        
        resolver = BlockchainResolver()
        
        assert resolver.poetry_path == "poetry"
        assert resolver.omen_script_path == "/path/to/omen"
        assert resolver.private_key == "0x123"
    
    def test_resolve_market_on_blockchain_yes_outcome(self, sample_market_status, test_helpers):
        """Test resolving market with Yes outcome"""
        resolver = BlockchainResolver()
        resolution_result = test_helpers.create_resolution_result(outcome="Yes")
        
        with patch.object(resolver, '_submit_outcome_resolution') as mock_submit:
            mock_submit.return_value = (True, "Success")
            
            success, message = resolver.resolve_market_on_blockchain(sample_market_status, resolution_result)
            
            assert success is True
            assert message == "Success"
            mock_submit.assert_called_once()
    
    def test_resolve_market_on_blockchain_invalid_outcome(self, sample_market_status, test_helpers):
        """Test resolving market with Invalid outcome"""
        resolver = BlockchainResolver()
        resolution_result = test_helpers.create_resolution_result(outcome="Invalid")
        
        with patch.object(resolver, '_submit_invalid_resolution') as mock_submit:
            mock_submit.return_value = (True, "Invalid resolution submitted")
            
            success, message = resolver.resolve_market_on_blockchain(sample_market_status, resolution_result)
            
            assert success is True
            assert message == "Invalid resolution submitted"
            mock_submit.assert_called_once()
    
    def test_resolve_market_on_blockchain_error(self, sample_market_status, sample_resolution_result):
        """Test error handling in resolve_market_on_blockchain"""
        resolver = BlockchainResolver()
        
        with patch.object(resolver, '_submit_outcome_resolution') as mock_submit:
            mock_submit.side_effect = Exception("Blockchain error")
            
            success, message = resolver.resolve_market_on_blockchain(sample_market_status, sample_resolution_result)
            
            assert success is False
            assert "Error resolving market on blockchain" in message
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.chmod')
    @patch('os.unlink')
    def test_execute_resolution_script_success(self, mock_unlink, mock_chmod, mock_temp_file, mock_subprocess):
        """Test successful script execution"""
        resolver = BlockchainResolver()
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess mock
        success_response = {"success": True, "message": "Transaction successful"}
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(success_response)
        mock_subprocess.return_value.stderr = ""
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success is True
        assert message == "Transaction successful"
        mock_chmod.assert_called_once_with("/tmp/test_script.py", 0o755)
        mock_unlink.assert_called_once_with("/tmp/test_script.py")
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.chmod')
    @patch('os.unlink')
    def test_execute_resolution_script_failure(self, mock_unlink, mock_chmod, mock_temp_file, mock_subprocess):
        """Test failed script execution"""
        resolver = BlockchainResolver()
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess mock for failure
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stdout = ""
        mock_subprocess.return_value.stderr = "Script error"
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success is False
        assert "Script error" in message
        mock_unlink.assert_called_once_with("/tmp/test_script.py")
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_execute_resolution_script_timeout(self, mock_temp_file, mock_subprocess):
        """Test script execution timeout"""
        resolver = BlockchainResolver()
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess timeout
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 300)
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success is False
        assert "timed out" in message
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.chmod')
    @patch('os.unlink')
    def test_execute_resolution_script_json_error_response(self, mock_unlink, mock_chmod, mock_temp_file, mock_subprocess):
        """Test script execution with JSON error response"""
        resolver = BlockchainResolver()
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess mock with error response
        error_response = {"success": False, "error": "Market not found"}
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(error_response)
        mock_subprocess.return_value.stderr = ""
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success is False
        assert message == "Market not found"
    
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.chmod')
    @patch('os.unlink')
    def test_execute_resolution_script_non_json_success(self, mock_unlink, mock_chmod, mock_temp_file, mock_subprocess):
        """Test script execution with non-JSON success output"""
        resolver = BlockchainResolver()
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess mock with non-JSON output
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Transaction completed successfully"
        mock_subprocess.return_value.stderr = ""
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success is True
        assert message == "Transaction completed successfully"
    
    def test_submit_outcome_resolution_yes(self, sample_market_status, test_helpers):
        """Test submitting Yes outcome resolution"""
        resolver = BlockchainResolver()
        resolution_result = test_helpers.create_resolution_result(outcome="Yes")
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            success, message = resolver._submit_outcome_resolution(sample_market_status, resolution_result, resolution_data)
            
            assert success is True
            assert message == "Success"
            mock_execute.assert_called_once()
            
            # Check that the script contains the expected outcome
            script_content = mock_execute.call_args[0][0]
            assert f'"{resolution_result.outcome}"' in script_content
            assert sample_market_status.market_id in script_content
    
    def test_submit_outcome_resolution_no(self, sample_market_status, test_helpers):
        """Test submitting No outcome resolution"""
        resolver = BlockchainResolver()
        resolution_result = test_helpers.create_resolution_result(outcome="No")
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            success, message = resolver._submit_outcome_resolution(sample_market_status, resolution_result, resolution_data)
            
            assert success is True
            mock_execute.assert_called_once()
            
            # Check that the script contains No outcome
            script_content = mock_execute.call_args[0][0]
            assert '"No"' in script_content
    
    def test_submit_outcome_resolution_error(self, sample_market_status, sample_resolution_result):
        """Test error in submitting outcome resolution"""
        resolver = BlockchainResolver()
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.side_effect = Exception("Script error")
            
            success, message = resolver._submit_outcome_resolution(sample_market_status, sample_resolution_result, resolution_data)
            
            assert success is False
            assert "Error submitting outcome resolution" in message
    
    def test_submit_invalid_resolution(self, sample_market_status):
        """Test submitting invalid resolution"""
        resolver = BlockchainResolver()
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Invalid resolution submitted")
            
            success, message = resolver._submit_invalid_resolution(sample_market_status, resolution_data)
            
            assert success is True
            assert message == "Invalid resolution submitted"
            mock_execute.assert_called_once()
            
            # Check that the script calls invalid resolution function
            script_content = mock_execute.call_args[0][0]
            assert "omen_submit_invalid_answer_market_tx" in script_content
            assert sample_market_status.market_id in script_content
    
    def test_submit_invalid_resolution_error(self, sample_market_status):
        """Test error in submitting invalid resolution"""
        resolver = BlockchainResolver()
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.side_effect = Exception("Invalid resolution error")
            
            success, message = resolver._submit_invalid_resolution(sample_market_status, resolution_data)
            
            assert success is False
            assert "Error submitting invalid resolution" in message
    
    def test_check_market_needs_final_resolution_yes(self):
        """Test checking market that needs final resolution"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, '{"needs_resolution": true, "message": "Answer provided, not resolved"}')
            
            needs_resolution, message = resolver.check_market_needs_final_resolution(market_id)
            
            assert needs_resolution is True
            assert "Answer provided, not resolved" in message
            mock_execute.assert_called_once()
    
    def test_check_market_needs_final_resolution_no(self):
        """Test checking market that doesn't need final resolution"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, '{"needs_resolution": false, "message": "Already resolved"}')
            
            needs_resolution, message = resolver.check_market_needs_final_resolution(market_id)
            
            assert needs_resolution is False
            assert "Already resolved" in message
    
    def test_check_market_needs_final_resolution_error(self):
        """Test error in checking final resolution status"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (False, "Script execution failed")
            
            needs_resolution, message = resolver.check_market_needs_final_resolution(market_id)
            
            assert needs_resolution is False
            assert "Script execution failed" in message
    
    def test_check_market_needs_final_resolution_json_parse_error(self):
        """Test JSON parsing error in final resolution check"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "invalid json response")
            
            needs_resolution, message = resolver.check_market_needs_final_resolution(market_id)
            
            assert needs_resolution is False
            assert "Could not parse check result" in message
    
    def test_finalize_market_resolution_success(self):
        """Test successful market finalization"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, '{"success": true, "message": "Market finalized"}')
            
            success, message = resolver.finalize_market_resolution(market_id)
            
            assert success is True
            assert message == '{"success": true, "message": "Market finalized"}'
            mock_execute.assert_called_once()
            
            # Check that the script calls the finalization function
            script_content = mock_execute.call_args[0][0]
            assert "omen_resolve_market_tx" in script_content
            assert market_id in script_content
    
    def test_finalize_market_resolution_error(self):
        """Test error in market finalization"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.side_effect = Exception("Finalization error")
            
            success, message = resolver.finalize_market_resolution(market_id)
            
            assert success is False
            assert "Error finalizing market resolution" in message


class TestBlockchainResolverScriptGeneration:
    """Tests for script generation in BlockchainResolver"""
    
    def test_outcome_resolution_script_content(self, sample_market_status, sample_resolution_result):
        """Test that outcome resolution script contains correct content"""
        resolver = BlockchainResolver()
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            resolver._submit_outcome_resolution(sample_market_status, sample_resolution_result, resolution_data)
            
            script_content = mock_execute.call_args[0][0]
            
            # Check essential components are in the script
            assert "sys.path.append" in script_content
            assert "APIKeys" in script_content
            assert "OmenSubgraphHandler" in script_content
            assert "omen_submit_answer_market_tx" in script_content
            assert sample_market_status.market_id in script_content
            assert resolver.private_key in script_content
            assert sample_resolution_result.outcome in script_content
    
    def test_invalid_resolution_script_content(self, sample_market_status):
        """Test that invalid resolution script contains correct content"""
        resolver = BlockchainResolver()
        resolution_data = {"test": "data"}
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            resolver._submit_invalid_resolution(sample_market_status, resolution_data)
            
            script_content = mock_execute.call_args[0][0]
            
            # Check essential components are in the script
            assert "omen_submit_invalid_answer_market_tx" in script_content
            assert sample_market_status.market_id in script_content
            assert "Invalid" in script_content
    
    def test_finalization_script_content(self):
        """Test that finalization script contains correct content"""
        resolver = BlockchainResolver()
        market_id = "0x1234"
        
        with patch.object(resolver, '_execute_resolution_script') as mock_execute:
            mock_execute.return_value = (True, "Success")
            
            resolver.finalize_market_resolution(market_id)
            
            script_content = mock_execute.call_args[0][0]
            
            # Check essential components are in the script
            assert "omen_resolve_market_tx" in script_content
            assert market_id in script_content
            assert "APIKeys" in script_content


@pytest.mark.parametrize("outcome,expected_function", [
    ("Yes", "omen_submit_answer_market_tx"),
    ("No", "omen_submit_answer_market_tx"),
    ("Invalid", "omen_submit_invalid_answer_market_tx"),
])
def test_resolution_function_selection(outcome, expected_function, sample_market_status, test_helpers):
    """Parametrized test for correct function selection based on outcome"""
    resolver = BlockchainResolver()
    resolution_result = test_helpers.create_resolution_result(outcome=outcome)
    
    with patch.object(resolver, '_execute_resolution_script') as mock_execute:
        mock_execute.return_value = (True, "Success")
        
        if outcome == "Invalid":
            resolver._submit_invalid_resolution(sample_market_status, {})
        else:
            resolver._submit_outcome_resolution(sample_market_status, resolution_result, {})
        
        script_content = mock_execute.call_args[0][0]
        assert expected_function in script_content


@pytest.mark.parametrize("returncode,stdout,stderr,expected_success", [
    (0, '{"success": true, "message": "OK"}', "", True),
    (0, '{"success": false, "error": "Failed"}', "", False),
    (1, "", "Error occurred", False),
    (0, "Non-JSON success message", "", True),
    (0, "invalid json", "", True),
])
def test_script_execution_response_handling(returncode, stdout, stderr, expected_success):
    """Parametrized test for different script execution responses"""
    resolver = BlockchainResolver()
    
    with patch('subprocess.run') as mock_subprocess, \
         patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
         patch('os.chmod'), \
         patch('os.unlink'):
        
        # Setup temp file mock
        mock_file = Mock()
        mock_file.name = "/tmp/test_script.py"
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Setup subprocess mock
        mock_subprocess.return_value.returncode = returncode
        mock_subprocess.return_value.stdout = stdout
        mock_subprocess.return_value.stderr = stderr
        
        success, message = resolver._execute_resolution_script("print('test')", "test_script")
        
        assert success == expected_success