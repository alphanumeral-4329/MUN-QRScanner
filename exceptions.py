"""
Custom Exceptions for MUN Scanner Application

This module defines custom exception classes that provide specific
error handling for different failure scenarios in the MUN Scanner system.
"""


class MUNScannerException(Exception):
    """
    Base exception for MUN Scanner application
    
    All custom exceptions in the MUN Scanner system should inherit
    from this base class for consistent error handling.
    """
    
    def __init__(self, message: str, error_code: str = None):
        """
        Initialize MUN Scanner exception
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self) -> str:
        """String representation of the exception"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class DelegateNotFoundException(MUNScannerException):
    """
    Raised when a delegate is not found in the system
    
    This exception is thrown when attempting to access or scan
    a delegate that doesn't exist in the delegates database.
    """
    
    def __init__(self, delegate_id: str):
        """
        Initialize delegate not found exception
        
        Args:
            delegate_id: The ID of the delegate that was not found
        """
        message = f"Delegate with ID '{delegate_id}' not found"
        super().__init__(message, "DELEGATE_NOT_FOUND")
        self.delegate_id = delegate_id


class AuthenticationFailedException(MUNScannerException):
    """
    Raised when authentication fails
    
    This exception is thrown when OC member login credentials
    are invalid or authentication process fails.
    """
    
    def __init__(self, oc_id: str = None):
        """
        Initialize authentication failed exception
        
        Args:
            oc_id: Optional OC ID that failed authentication
        """
        if oc_id:
            message = f"Authentication failed for OC ID '{oc_id}'"
        else:
            message = "Authentication failed - invalid credentials"
        super().__init__(message, "AUTH_FAILED")
        self.oc_id = oc_id


class DataValidationException(MUNScannerException):
    """
    Raised when data validation fails
    
    This exception is thrown when input data doesn't meet
    the required validation criteria.
    """
    
    def __init__(self, field_name: str, validation_error: str):
        """
        Initialize data validation exception
        
        Args:
            field_name: Name of the field that failed validation
            validation_error: Description of the validation error
        """
        message = f"Validation error in field '{field_name}': {validation_error}"
        super().__init__(message, "VALIDATION_ERROR")
        self.field_name = field_name
        self.validation_error = validation_error


class DataAccessException(MUNScannerException):
    """
    Raised when data access operations fail
    
    This exception is thrown when there are issues reading from
    or writing to data storage (JSON files, databases, etc.).
    """
    
    def __init__(self, operation: str, details: str):
        """
        Initialize data access exception
        
        Args:
            operation: The operation that failed (e.g., 'read', 'write')
            details: Detailed error information
        """
        message = f"Data access error during {operation}: {details}"
        super().__init__(message, "DATA_ACCESS_ERROR")
        self.operation = operation
        self.details = details


class AttendanceException(MUNScannerException):
    """
    Raised when attendance operations fail
    
    This exception is thrown when there are issues with
    attendance marking or tracking operations.
    """
    
    def __init__(self, delegate_id: str, operation: str, reason: str):
        """
        Initialize attendance exception
        
        Args:
            delegate_id: ID of the delegate involved
            operation: The attendance operation that failed
            reason: Reason for the failure
        """
        message = f"Attendance {operation} failed for delegate '{delegate_id}': {reason}"
        super().__init__(message, "ATTENDANCE_ERROR")
        self.delegate_id = delegate_id
        self.operation = operation
        self.reason = reason
