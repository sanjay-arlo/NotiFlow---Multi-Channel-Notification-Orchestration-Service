"""
Unit tests for retry logic and backoff strategies.
"""

import pytest
from datetime import datetime, timedelta

from app.core.constants import CHANNEL_RETRY_CONFIG
from app.utils.retry import (
    calculate_backoff,
    get_max_attempts,
    is_retryable_error,
    is_permanent_error,
    get_retry_schedule
)


class TestRetryLogic:
    """Test cases for retry logic."""
    
    def test_calculate_backoff_email(self):
        """Test exponential backoff calculation for email."""
        # Test base delay
        delay = calculate_backoff(0, "email")
        assert delay == 60  # Base delay for email
        
        # Test exponential growth
        delay = calculate_backoff(1, "email")
        assert delay == 120  # 60 * 2^1
        
        delay = calculate_backoff(2, "email")
        assert delay == 240  # 60 * 2^2
        
        # Test max delay cap
        delay = calculate_backoff(10, "email")
        assert delay == 3600  # Max cap for email
    
    def test_calculate_backoff_sms(self):
        """Test exponential backoff calculation for SMS."""
        # Test base delay
        delay = calculate_backoff(0, "sms")
        assert delay == 30  # Base delay for SMS
        
        # Test exponential growth
        delay = calculate_backoff(1, "sms")
        assert delay == 60  # 30 * 2^1
        
        delay = calculate_backoff(2, "sms")
        assert delay == 120  # 30 * 2^2
        
        # Test max delay cap
        delay = calculate_backoff(8, "sms")
        assert delay == 1800  # Max cap for SMS
    
    def test_calculate_backoff_webhook(self):
        """Test exponential backoff calculation for webhook."""
        # Test base delay
        delay = calculate_backoff(0, "webhook")
        assert delay == 10  # Base delay for webhook
        
        # Test exponential growth
        delay = calculate_backoff(1, "webhook")
        assert delay == 20  # 10 * 2^1
        
        delay = calculate_backoff(2, "webhook")
        assert delay == 40  # 10 * 2^2
        
        # Test max delay cap
        delay = calculate_backoff(8, "webhook")
        assert delay == 600  # Max cap for webhook
    
    def test_calculate_backoff_with_retry_after(self):
        """Test backoff calculation with explicit retry_after."""
        # retry_after should override calculated delay
        delay = calculate_backoff(0, "email", retry_after=300)
        assert delay == 300  # Should use retry_after
        
        delay = calculate_backoff(1, "email", retry_after=120)
        assert delay == 120  # Should use retry_after
    
    def test_calculate_backoff_with_jitter(self):
        """Test that jitter is added to delay."""
        # Run multiple times to test jitter randomness
        delays = []
        for _ in range(10):
            delay = calculate_backoff(0, "email")
            delays.append(delay)
        
        # All delays should be close to base delay with some jitter
        base_delay = 60
        jitter_range = base_delay * 0.1  # 10% jitter
        
        for delay in delays:
            assert base_delay - jitter_range <= delay <= base_delay + jitter_range
    
    def test_get_max_attempts(self):
        """Test getting max attempts for different channels."""
        assert get_max_attempts("email") == 4
        assert get_max_attempts("sms") == 3
        assert get_max_attempts("webhook") == 5
        assert get_max_attempts("unknown") == 3  # Default fallback
    
    def test_is_retryable_error_email(self):
        """Test retryable error detection for email."""
        # Test retryable SMTP error codes
        assert is_retryable_error("email", "421") is True  # Service not available
        assert is_retryable_error("email", "450") is True  # Requested mail action not taken
        assert is_retryable_error("email", "451") is True  # Requested action aborted
        assert is_retryable_error("email", "452") is True  # Insufficient system storage
        assert is_retryable_error("email", "454") is True  # Temporary authentication failure
        
        # Test non-retryable error codes
        assert is_retryable_error("email", "550") is False  # Requested action not taken
        assert is_retryable_error("email", "551") is False  # User unknown
        assert is_retryable_error("email", "554") is False  # Transaction failed
    
    def test_is_retryable_error_sms(self):
        """Test retryable error detection for SMS."""
        # Test retryable Twilio error codes
        assert is_retryable_error("sms", "21614") is True  # 'To' number is not a valid mobile number
        assert is_retryable_error("sms", "21612") is True  # 'To' number is not currently reachable
        assert is_retryable_error("sms", "21610") is True  # Attempt to send to unsubscribed recipient
        assert is_retryable_error("sms", "21629") is True  # Message rate limit exceeded
        assert is_retryable_error("sms", "21630") is True  # Message rate limit exceeded
        
        # Test non-retryable error codes
        assert is_retryable_error("sms", "21211") is False  # Invalid 'To' phone number
        assert is_retryable_error("sms", "21408") is False  # Permission to send message denied
        assert is_retryable_error("sms", "21607") is False  # Blocked destination
    
    def test_is_retryable_error_webhook(self):
        """Test retryable error detection for webhook."""
        # Test retryable HTTP status codes
        assert is_retryable_error("webhook", "429") is True  # Too Many Requests
        assert is_retryable_error("webhook", "500") is True  # Internal Server Error
        assert is_retryable_error("webhook", "502") is True  # Bad Gateway
        assert is_retryable_error("webhook", "503") is True  # Service Unavailable
        assert is_retryable_error("webhook", "504") is True  # Gateway Timeout
        
        # Test non-retryable error codes
        assert is_retryable_error("webhook", "400") is False  # Bad Request
        assert is_retryable_error("webhook", "401") is False  # Unauthorized
        assert is_retryable_error("webhook", "403") is False  # Forbidden
        assert is_retryable_error("webhook", "404") is False  # Not Found
        assert is_retryable_error("webhook", "408") is False  # Request Timeout
    
    def test_is_permanent_error_email(self):
        """Test permanent error detection for email."""
        # Test permanent SMTP error codes
        assert is_permanent_error("email", "550") is True  # Requested action not taken
        assert is_permanent_error("email", "551") is True  # User unknown
        assert is_permanent_error("email", "554") is True  # Transaction failed
        
        # Test non-permanent error codes
        assert is_permanent_error("email", "421") is False  # Service not available
        assert is_permanent_error("email", "450") is False  # Requested mail action not taken
    
    def test_is_permanent_error_sms(self):
        """Test permanent error detection for SMS."""
        # Test permanent Twilio error codes
        assert is_permanent_error("sms", "21211") is True  # Invalid 'To' phone number
        assert is_permanent_error("sms", "21408") is True  # Permission to send message denied
        assert is_permanent_error("sms", "21607") is True  # Blocked destination
        
        # Test non-permanent error codes
        assert is_permanent_error("sms", "21614") is False  # 'To' number is not a valid mobile number
        assert is_permanent_error("sms", "21612") is False  # 'To' number is not currently reachable
    
    def test_is_permanent_error_webhook(self):
        """Test permanent error detection for webhook."""
        # Test permanent HTTP status codes
        assert is_permanent_error("webhook", "400") is True  # Bad Request
        assert is_permanent_error("webhook", "401") is True  # Unauthorized
        assert is_permanent_error("webhook", "403") is True  # Forbidden
        assert is_permanent_error("webhook", "404") is True  # Not Found
        assert is_permanent_error("webhook", "408") is True  # Request Timeout
        
        # Test non-permanent error codes
        assert is_permanent_error("webhook", "429") is False  # Too Many Requests
        assert is_permanent_error("webhook", "500") is False  # Internal Server Error
        assert is_permanent_error("webhook", "502") is False  # Bad Gateway
    
    def test_get_retry_schedule(self):
        """Test getting retry schedule for channels."""
        # Test email schedule
        email_schedule = get_retry_schedule("email")
        assert len(email_schedule) == 4  # Max attempts
        assert email_schedule[0] == 60
        assert email_schedule[1] == 120
        assert email_schedule[2] == 240
        assert email_schedule[3] == 3600  # Max cap
        
        # Test SMS schedule
        sms_schedule = get_retry_schedule("sms")
        assert len(sms_schedule) == 3  # Max attempts
        assert sms_schedule[0] == 30
        assert sms_schedule[1] == 60
        assert sms_schedule[2] == 120
        
        # Test webhook schedule
        webhook_schedule = get_retry_schedule("webhook")
        assert len(webhook_schedule) == 5  # Max attempts
        assert webhook_schedule[0] == 10
        assert webhook_schedule[1] == 20
        assert webhook_schedule[2] == 40
        assert webhook_schedule[3] == 80
        assert webhook_schedule[4] == 160
    
    def test_calculate_next_retry_at(self):
        """Test calculating next retry timestamp."""
        from app.utils.retry import calculate_next_retry_at
        
        # Test without retry_after
        next_retry = calculate_next_retry_at(0, "email")
        expected = datetime.utcnow() + timedelta(seconds=60)
        assert abs((next_retry - expected).total_seconds()) < 1  # Within 1 second
        
        # Test with retry_after
        next_retry = calculate_next_retry_at(0, "email", retry_after=300)
        expected = datetime.utcnow() + timedelta(seconds=300)
        assert abs((next_retry - expected).total_seconds()) < 1  # Within 1 second
    
    def test_should_retry_delivery(self):
        """Test delivery retry logic."""
        from app.utils.retry import should_retry_delivery
        
        # Test retryable delivery
        delivery = type('Delivery', (), {
            'status': 'failed',
            'attempt_count': 1,
            'max_attempts': 3,
            'next_retry_at': datetime.utcnow() - timedelta(seconds=1),  # Past
            'error_code': '421'
        })
        
        assert should_retry_delivery(
            delivery, 3, 'email', error_code='421'
        ) is True
        
        # Test non-retryable delivery
        delivery.error_code = '550'
        assert should_retry_delivery(
            delivery, 3, 'email', error_code='550'
        ) is False
        
        # Test max attempts reached
        delivery.attempt_count = 3
        delivery.error_code = '421'
        assert should_retry_delivery(
            delivery, 3, 'email', error_code='421'
        ) is False
        
        # Test future retry time
        delivery.attempt_count = 1
        delivery.next_retry_at = datetime.utcnow() + timedelta(minutes=5)  # Future
        delivery.error_code = '421'
        assert should_retry_delivery(
            delivery, 3, 'email', error_code='421'
        ) is False
    
    def test_get_example_retry_schedules(self):
        """Test getting example retry schedules."""
        from app.utils.retry import get_example_retry_schedules
        
        schedules = get_example_retry_schedules()
        
        assert 'email' in schedules
        assert 'sms' in schedules
        assert 'webhook' in schedules
        
        # Check that schedules are lists of integers
        for channel, schedule in schedules.items():
            assert isinstance(schedule, list)
            for delay in schedule:
                assert isinstance(delay, int)
                assert delay > 0
