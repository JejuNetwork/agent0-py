"""
Test for Agent Validation Flow
Tests the full validation lifecycle:
1. Request validation from a validator
2. Validator responds with a score
3. Query validation status
4. Get validation summary

Usage:
    Update AGENT_ID constant in config.py to point to your existing agent

Note: This test requires two different wallets:
- AGENT_PRIVATE_KEY: The agent owner who requests validation
- VALIDATOR_PRIVATE_KEY: The validator who responds (uses CLIENT_PRIVATE_KEY from env)
"""

import logging
import time
import sys
import pytest
from web3 import Web3

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logging.getLogger('agent0_sdk').setLevel(logging.DEBUG)

from agent0_sdk import SDK
from config import CHAIN_ID, RPC_URL, AGENT_PRIVATE_KEY, PINATA_JWT, AGENT_ID, print_config

# Validator configuration (use CLIENT_PRIVATE_KEY as validator for testing)
VALIDATOR_PRIVATE_KEY = "f8d368064ccf80769e348a59155f69ec224849bd507a8c26dd85beefa777331a"


class TestValidationFlow:
    """Test validation lifecycle."""
    
    agent_sdk: SDK = None
    validator_sdk: SDK = None
    validator_address: str = None
    request_hash: str = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup SDKs for testing."""
        print_config()
        
        if not AGENT_PRIVATE_KEY or AGENT_PRIVATE_KEY.strip() == '':
            pytest.skip("AGENT_PRIVATE_KEY is required for validation tests. Set it in .env file.")
        
        sdk_config = {
            "chainId": CHAIN_ID,
            "rpcUrl": RPC_URL,
            "ipfs": "pinata",
            "pinataJwt": PINATA_JWT,
        }
        
        # Agent SDK with signer
        self.__class__.agent_sdk = SDK(
            chainId=sdk_config["chainId"],
            rpcUrl=sdk_config["rpcUrl"],
            signer=AGENT_PRIVATE_KEY,
            ipfs=sdk_config["ipfs"],
            pinataJwt=sdk_config["pinataJwt"],
        )
        
        # Validator SDK with signer
        self.__class__.validator_sdk = SDK(
            chainId=sdk_config["chainId"],
            rpcUrl=sdk_config["rpcUrl"],
            signer=VALIDATOR_PRIVATE_KEY,
            ipfs=sdk_config["ipfs"],
            pinataJwt=sdk_config["pinataJwt"],
        )
        self.__class__.validator_address = self.validator_sdk.web3_client.account.address

    def test_01_initialize_sdks(self):
        """Test SDK initialization."""
        assert self.agent_sdk is not None
        assert self.validator_sdk is not None
        assert self.validator_address is not None
        assert self.validator_address.startswith("0x")

    def test_02_request_validation(self):
        """Test requesting validation from validator."""
        # Generate a unique request hash
        request_data = f"validation-request-{int(time.time())}"
        self.__class__.request_hash = Web3.keccak(text=request_data).hex()
        
        request_uri = f"ipfs://QmValidationRequest{int(time.time())}"
        
        # Agent requests validation
        tx_hash = self.agent_sdk.requestValidation(
            AGENT_ID,
            self.validator_address,
            request_uri,
            self.request_hash
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith("0x")
        
        # Wait for transaction confirmation
        time.sleep(5)

    def test_03_get_validation_status_before_response(self):
        """Test getting validation status before response."""
        status = self.agent_sdk.getValidationStatus(self.request_hash)
        
        assert status is not None
        assert status["validatorAddress"].lower() == self.validator_address.lower()
        assert status["response"] == 0  # No response yet
        assert status["lastUpdate"] > 0

    def test_04_respond_to_validation(self):
        """Test validator responding to validation request."""
        response = 85  # 85% pass score
        response_uri = f"ipfs://QmValidationResponse{int(time.time())}"
        response_hash = Web3.keccak(text=f"response-{time.time()}").hex()
        tag = Web3.keccak(text="quality-check").hex()
        
        # Validator responds
        tx_hash = self.validator_sdk.respondToValidation(
            self.request_hash,
            response,
            response_uri,
            response_hash,
            tag
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith("0x")
        
        # Wait for transaction confirmation
        time.sleep(5)

    def test_05_get_validation_status_after_response(self):
        """Test getting validation status after response."""
        status = self.agent_sdk.getValidationStatus(self.request_hash)
        
        assert status is not None
        assert status["validatorAddress"].lower() == self.validator_address.lower()
        assert status["response"] == 85
        assert status["tag"] is not None

    def test_06_get_agent_validations(self):
        """Test getting agent's validation list."""
        validations = self.agent_sdk.getAgentValidations(AGENT_ID)
        
        assert isinstance(validations, list)
        assert len(validations) > 0
        # The request hash we created should be in the list
        assert any(v.lower() == self.request_hash.lower() for v in validations)

    def test_07_get_validator_requests(self):
        """Test getting validator's request list."""
        requests = self.agent_sdk.getValidatorRequests(self.validator_address)
        
        assert isinstance(requests, list)
        assert len(requests) > 0
        # The request hash we created should be in the list
        assert any(r.lower() == self.request_hash.lower() for r in requests)

    def test_08_get_validation_summary(self):
        """Test getting validation summary."""
        summary = self.agent_sdk.getValidationSummary(AGENT_ID)
        
        assert summary is not None
        assert summary["agentId"] == AGENT_ID
        assert summary["count"] > 0
        assert 0 <= summary["avgResponse"] <= 100

    def test_09_get_validation_summary_filtered(self):
        """Test getting validation summary filtered by validator."""
        summary = self.agent_sdk.getValidationSummary(AGENT_ID, [self.validator_address])
        
        assert summary is not None
        assert summary["count"] > 0

    def test_10_reject_invalid_response(self):
        """Test that response > 100 is rejected."""
        # Generate new request hash for this test
        new_request_data = f"validation-request-reject-{int(time.time())}"
        new_request_hash = Web3.keccak(text=new_request_data).hex()
        
        # First create the request
        self.agent_sdk.requestValidation(
            AGENT_ID,
            self.validator_address,
            "ipfs://QmRejectTest",
            new_request_hash
        )
        
        time.sleep(5)
        
        # Try to respond with invalid score - should raise ValueError
        with pytest.raises(ValueError, match="Response must be between 0 and 100"):
            self.validator_sdk.respondToValidation(new_request_hash, 101)


class TestAgentValidationMethods:
    """Test Agent class validation methods."""
    
    sdk: SDK = None
    validator_sdk: SDK = None
    validator_address: str = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup SDKs for testing."""
        if not AGENT_PRIVATE_KEY or AGENT_PRIVATE_KEY.strip() == '':
            pytest.skip("AGENT_PRIVATE_KEY is required")
        
        self.__class__.sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=AGENT_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        
        self.__class__.validator_sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=VALIDATOR_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        self.__class__.validator_address = self.validator_sdk.web3_client.account.address

    def test_01_request_validation_via_agent(self):
        """Test requesting validation through Agent class."""
        agent = self.sdk.loadAgent(AGENT_ID)
        assert agent.agentId == AGENT_ID
        
        request_data = f"agent-validation-{int(time.time())}"
        request_hash = Web3.keccak(text=request_data).hex()
        
        tx_hash = agent.requestValidation(
            self.validator_address,
            "ipfs://QmAgentValidation",
            request_hash
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith("0x")
        
        time.sleep(5)
        
        # Respond to this validation
        self.validator_sdk.respondToValidation(request_hash, 90)
        
        time.sleep(5)

    def test_02_get_validations_via_agent(self):
        """Test getting validations through Agent class."""
        agent = self.sdk.loadAgent(AGENT_ID)
        
        validations = agent.getValidations()
        assert isinstance(validations, list)
        assert len(validations) > 0

    def test_03_get_validation_summary_via_agent(self):
        """Test getting validation summary through Agent class."""
        agent = self.sdk.loadAgent(AGENT_ID)
        
        summary = agent.getValidationSummary()
        assert summary is not None
        assert summary["count"] > 0
        assert 0 <= summary["avgResponse"] <= 100


class TestValidationBoundaryConditions:
    """Test validation boundary conditions."""
    
    agent_sdk: SDK = None
    validator_sdk: SDK = None
    validator_address: str = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup SDKs for testing."""
        if not AGENT_PRIVATE_KEY or AGENT_PRIVATE_KEY.strip() == '':
            pytest.skip("AGENT_PRIVATE_KEY is required")
        
        self.__class__.agent_sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=AGENT_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        
        self.__class__.validator_sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=VALIDATOR_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        self.__class__.validator_address = self.validator_sdk.web3_client.account.address

    def test_01_accept_score_zero(self):
        """Score 0 is accepted."""
        request_hash = Web3.keccak(text=f"validation-score-zero-{int(time.time())}").hex()
        self.agent_sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmScoreZero", request_hash)
        time.sleep(5)
        
        tx_hash = self.validator_sdk.respondToValidation(request_hash, 0)
        assert tx_hash is not None
        time.sleep(5)
        
        status = self.agent_sdk.getValidationStatus(request_hash)
        assert status is not None
        assert status["response"] == 0

    def test_02_accept_score_hundred(self):
        """Score 100 is accepted."""
        request_hash = Web3.keccak(text=f"validation-score-hundred-{int(time.time())}").hex()
        self.agent_sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmScoreHundred", request_hash)
        time.sleep(5)
        
        tx_hash = self.validator_sdk.respondToValidation(request_hash, 100)
        assert tx_hash is not None
        time.sleep(5)
        
        status = self.agent_sdk.getValidationStatus(request_hash)
        assert status is not None
        assert status["response"] == 100

    def test_03_reject_negative_score(self):
        """Negative score is rejected."""
        request_hash = Web3.keccak(text=f"negative-{int(time.time())}").hex()
        with pytest.raises(ValueError, match="Response must be between 0 and 100"):
            self.validator_sdk.respondToValidation(request_hash, -1)

    def test_04_accept_intermediate_score(self):
        """Intermediate score 50 is accepted."""
        request_hash = Web3.keccak(text=f"validation-score-fifty-{int(time.time())}").hex()
        self.agent_sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmScoreFifty", request_hash)
        time.sleep(5)
        
        self.validator_sdk.respondToValidation(request_hash, 50)
        time.sleep(5)
        
        status = self.agent_sdk.getValidationStatus(request_hash)
        assert status["response"] == 50


class TestValidationEdgeCases:
    """Test validation edge cases."""
    
    sdk: SDK = None
    validator_sdk: SDK = None
    validator_address: str = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup SDKs for testing."""
        if not AGENT_PRIVATE_KEY or AGENT_PRIVATE_KEY.strip() == '':
            pytest.skip("AGENT_PRIVATE_KEY is required")
        
        self.__class__.sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=AGENT_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        
        self.__class__.validator_sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=VALIDATOR_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        self.__class__.validator_address = self.validator_sdk.web3_client.account.address

    def test_01_non_existent_request_hash(self):
        """Test getting status for non-existent requestHash."""
        non_existent_hash = Web3.keccak(text=f"non-existent-{int(time.time())}").hex()
        status = self.sdk.getValidationStatus(non_existent_hash)
        
        # Non-existent validation should return None or have zero validator address
        zero_addr = "0x" + "00" * 20
        assert status is None or status.get("validatorAddress", "").lower() == zero_addr.lower()

    def test_02_empty_validator_filter_in_summary(self):
        """Test summary with empty validator filter."""
        summary = self.sdk.getValidationSummary(AGENT_ID, [])
        
        assert summary is not None
        assert summary["agentId"] == AGENT_ID
        assert isinstance(summary["count"], int)
        assert isinstance(summary["avgResponse"], (int, float))

    def test_03_agent_with_no_validations(self):
        """Test summary for agent with no validations."""
        non_existent_agent = "999999999:999999999"
        summary = self.sdk.getValidationSummary(non_existent_agent)
        
        assert summary is not None
        assert summary["count"] == 0

    def test_04_empty_validations_list(self):
        """Test getAgentValidations for agent with no validations."""
        non_existent_agent = "999999999:999999999"
        validations = self.sdk.getAgentValidations(non_existent_agent)
        
        assert isinstance(validations, list)
        assert len(validations) == 0

    def test_05_empty_validator_requests_list(self):
        """Test getValidatorRequests for address with no requests."""
        from eth_account import Account
        random_address = Account.create().address
        requests = self.sdk.getValidatorRequests(random_address)
        
        assert isinstance(requests, list)
        assert len(requests) == 0

    def test_06_request_with_minimal_parameters(self):
        """Test request with minimal/empty URI."""
        request_data = f"minimal-request-{int(time.time())}"
        request_hash = Web3.keccak(text=request_data).hex()
        
        tx_hash = self.sdk.requestValidation(
            AGENT_ID,
            self.validator_address,
            "",  # empty URI
            request_hash
        )
        
        assert tx_hash is not None
        assert tx_hash.startswith("0x")

    def test_07_response_with_minimal_parameters(self):
        """Test response with only required params."""
        request_data = f"minimal-response-{int(time.time())}"
        request_hash = Web3.keccak(text=request_data).hex()
        
        self.sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmMinimal", request_hash)
        time.sleep(5)
        
        tx_hash = self.validator_sdk.respondToValidation(request_hash, 75)
        
        assert tx_hash is not None
        assert tx_hash.startswith("0x")
        
        time.sleep(5)
        
        status = self.sdk.getValidationStatus(request_hash)
        assert status["response"] == 75


class TestValidationDataInspection:
    """Test that actual data matches expected values."""
    
    sdk: SDK = None
    validator_sdk: SDK = None
    validator_address: str = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup SDKs for testing."""
        if not AGENT_PRIVATE_KEY or AGENT_PRIVATE_KEY.strip() == '':
            pytest.skip("AGENT_PRIVATE_KEY is required")
        
        self.__class__.sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=AGENT_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        
        self.__class__.validator_sdk = SDK(
            chainId=CHAIN_ID,
            rpcUrl=RPC_URL,
            signer=VALIDATOR_PRIVATE_KEY,
            ipfs="pinata",
            pinataJwt=PINATA_JWT,
        )
        self.__class__.validator_address = self.validator_sdk.web3_client.account.address

    def test_01_verify_all_status_fields(self):
        """Verify all ValidationStatus fields match expected values."""
        ts = int(time.time())
        request_data = f"data-inspection-{ts}"
        request_hash = Web3.keccak(text=request_data).hex()
        request_uri = f"ipfs://QmInspection{ts}"
        response_uri = f"ipfs://QmResponseInspection{ts}"
        response_hash_input = Web3.keccak(text=f"response-data-{ts}").hex()
        tag_input = Web3.keccak(text="data-inspection-tag").hex()
        expected_score = 87
        
        # Create request
        self.sdk.requestValidation(AGENT_ID, self.validator_address, request_uri, request_hash)
        time.sleep(5)
        
        # Verify initial state
        before_status = self.sdk.getValidationStatus(request_hash)
        assert before_status is not None
        assert before_status["validatorAddress"].lower() == self.validator_address.lower()
        assert before_status["response"] == 0
        
        # Submit response with all parameters
        self.validator_sdk.respondToValidation(
            request_hash,
            expected_score,
            response_uri,
            response_hash_input,
            tag_input
        )
        time.sleep(5)
        
        # Verify all fields after response
        after_status = self.sdk.getValidationStatus(request_hash)
        assert after_status is not None
        assert after_status["validatorAddress"].lower() == self.validator_address.lower()
        assert after_status["response"] == expected_score
        assert after_status["responseHash"] == response_hash_input
        assert after_status["tag"] == tag_input
        assert after_status["lastUpdate"] > 0

    def test_02_verify_agent_validations_contains_hash(self):
        """Verify getAgentValidations returns correct hashes."""
        ts = int(time.time())
        request_hash = Web3.keccak(text=f"agent-validations-{ts}").hex()
        
        self.sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmAgentVal", request_hash)
        time.sleep(5)
        
        validations = self.sdk.getAgentValidations(AGENT_ID)
        
        assert isinstance(validations, list)
        assert len(validations) > 0
        
        # Verify our request hash is in the list
        found = any(v.lower() == request_hash.lower() for v in validations)
        assert found, f"Request hash {request_hash} not found in validations"

    def test_03_verify_validator_requests_contains_hash(self):
        """Verify getValidatorRequests returns correct hashes."""
        ts = int(time.time())
        request_hash = Web3.keccak(text=f"validator-requests-{ts}").hex()
        
        self.sdk.requestValidation(AGENT_ID, self.validator_address, "ipfs://QmValidatorReq", request_hash)
        time.sleep(5)
        
        requests = self.sdk.getValidatorRequests(self.validator_address)
        
        assert isinstance(requests, list)
        assert len(requests) > 0
        
        # Verify our request hash is in the list
        found = any(r.lower() == request_hash.lower() for r in requests)
        assert found, f"Request hash {request_hash} not found in validator requests"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
