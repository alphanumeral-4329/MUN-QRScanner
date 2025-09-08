"""
MUN Scanner Package

A Model UN delegate scanning and attendance tracking system built with Flask.
This package provides a complete web application for managing delegate attendance
at Model UN conferences using QR code scanning.

Main Components:
- models: Data models for delegates, attendance records, and OC members
- repositories: Data access layer with repository pattern
- services: Business logic layer for authentication, delegates, and attendance
- exceptions: Custom exception classes for error handling
- app: Main Flask application class

Usage:
    from app import create_app
    
    app = create_app()
    app.run()
"""

__version__ = "1.0.0"
__author__ = "MUN Scanner Team"
__email__ = "contact@munscanner.org"

# Import main components for easy access
from .app import create_app, create_development_app, create_production_app
from .models import Delegate, AttendanceRecord, OrganizingCommittee, FormStatus
from .services import AuthenticationService, DelegateService, AttendanceService
from .repositories import RepositoryFactory
from .exceptions import (
    MUNScannerException,
    DelegateNotFoundException,
    AuthenticationFailedException,
    AttendanceException,
    DataValidationException,
    DataAccessException
)

__all__ = [
    # App factory functions
    'create_app',
    'create_development_app', 
    'create_production_app',
    
    # Data models
    'Delegate',
    'AttendanceRecord',
    'OrganizingCommittee',
    'FormStatus',
    
    # Services
    'AuthenticationService',
    'DelegateService', 
    'AttendanceService',
    
    # Repository factory
    'RepositoryFactory',
    
    # Exceptions
    'MUNScannerException',
    'DelegateNotFoundException',
    'AuthenticationFailedException',
    'AttendanceException',
    'DataValidationException',
    'DataAccessException'
]
