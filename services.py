"""
Business Logic Services for MUN Scanner Application

This module contains service classes that implement the core business logic
of the MUN Scanner system. Services handle authentication, delegate management,
and attendance tracking with proper validation and error handling.
"""

from typing import Dict, Optional, List
from models import Delegate, AttendanceRecord, OrganizingCommittee, FormStatus
from repositories import DataRepository
from exceptions import (
    AuthenticationFailedException, 
    DelegateNotFoundException,
    AttendanceException,
    DataValidationException
)


class AuthenticationService:
    """
    Handles authentication and authorization logic
    
    This service manages OC member authentication, session validation,
    and access control throughout the application.
    """
    
    def __init__(self, oc_repository: DataRepository):
        """
        Initialize authentication service
        
        Args:
            oc_repository: Repository for OC member data
        """
        self.oc_repository = oc_repository
        self._oc_members: Dict[str, OrganizingCommittee] = {}
        self._load_oc_members()
    
    def _load_oc_members(self) -> None:
        """
        Load OC members from repository
        
        Raises:
            DataValidationException: If OC data is invalid
        """
        try:
            oc_data = self.oc_repository.load_data()
            self._oc_members = {}
            
            for oc_id, password in oc_data.items():
                if not isinstance(oc_id, str) or not isinstance(password, str):
                    raise DataValidationException(
                        "oc_credentials", 
                        f"Invalid OC credentials format for {oc_id}"
                    )
                
                if not oc_id.strip() or not password.strip():
                    raise DataValidationException(
                        "oc_credentials", 
                        f"Empty OC ID or password for {oc_id}"
                    )
                
                self._oc_members[oc_id] = OrganizingCommittee(oc_id, password)
                
        except Exception as e:
            if isinstance(e, DataValidationException):
                raise
            raise DataValidationException("oc_data", f"Failed to load OC data: {str(e)}")
    
    def authenticate(self, oc_id: str, password: str) -> bool:
        """
        Authenticate OC member credentials
        
        Args:
            oc_id: OC member ID
            password: Password to verify
            
        Returns:
            True if authentication successful, False otherwise
            
        Raises:
            AuthenticationFailedException: If authentication fails
        """
        if not oc_id or not password:
            raise AuthenticationFailedException()
        
        if oc_id not in self._oc_members:
            raise AuthenticationFailedException(oc_id)
        
        is_valid = self._oc_members[oc_id].verify_password(password)
        if not is_valid:
            raise AuthenticationFailedException(oc_id)
        
        return True
    
    def get_oc_member(self, oc_id: str) -> Optional[OrganizingCommittee]:
        """
        Get OC member by ID
        
        Args:
            oc_id: OC member ID
            
        Returns:
            OrganizingCommittee instance or None if not found
        """
        return self._oc_members.get(oc_id)
    
    def is_valid_oc_id(self, oc_id: str) -> bool:
        """
        Check if OC ID is valid
        
        Args:
            oc_id: OC member ID to validate
            
        Returns:
            True if OC ID exists
        """
        return oc_id in self._oc_members
    
    def get_all_oc_members(self) -> List[OrganizingCommittee]:
        """
        Get all OC members
        
        Returns:
            List of all OC members
        """
        return list(self._oc_members.values())


class DelegateService:
    """
    Handles delegate-related operations and business logic
    
    This service manages delegate information, validation,
    and provides various delegate-related queries.
    """
    
    def __init__(self, delegate_repository: DataRepository):
        """
        Initialize delegate service
        
        Args:
            delegate_repository: Repository for delegate data
        """
        self.delegate_repository = delegate_repository
        self._delegates: Dict[str, Delegate] = {}
        self._load_delegates()
    
    def _load_delegates(self) -> None:
        """
        Load delegates from repository
        
        Raises:
            DataValidationException: If delegate data is invalid
        """
        try:
            delegate_data = self.delegate_repository.load_data()
            self._delegates = {}
            
            for delegate_id, data in delegate_data.items():
                try:
                    delegate = Delegate.from_dict(delegate_id, data)
                    self._delegates[delegate_id] = delegate
                except (KeyError, ValueError) as e:
                    raise DataValidationException(
                        f"delegate_{delegate_id}", 
                        f"Invalid delegate data: {str(e)}"
                    )
                    
        except Exception as e:
            if isinstance(e, DataValidationException):
                raise
            raise DataValidationException("delegate_data", f"Failed to load delegates: {str(e)}")
    
    def get_delegate(self, delegate_id: str) -> Optional[Delegate]:
        """
        Get delegate by ID
        
        Args:
            delegate_id: Delegate ID
            
        Returns:
            Delegate instance or None if not found
        """
        return self._delegates.get(delegate_id)
    
    def get_delegate_or_raise(self, delegate_id: str) -> Delegate:
        """
        Get delegate by ID or raise exception if not found
        
        Args:
            delegate_id: Delegate ID
            
        Returns:
            Delegate instance
            
        Raises:
            DelegateNotFoundException: If delegate not found
        """
        delegate = self.get_delegate(delegate_id)
        if not delegate:
            raise DelegateNotFoundException(delegate_id)
        return delegate
    
    def get_all_delegates(self) -> List[Delegate]:
        """
        Get all delegates
        
        Returns:
            List of all delegates
        """
        return list(self._delegates.values())
    
    def delegate_exists(self, delegate_id: str) -> bool:
        """
        Check if delegate exists
        
        Args:
            delegate_id: Delegate ID to check
            
        Returns:
            True if delegate exists
        """
        return delegate_id in self._delegates
    
    def get_delegates_by_committee(self, committee: str) -> List[Delegate]:
        """
        Get all delegates in a specific committee
        
        Args:
            committee: Committee name
            
        Returns:
            List of delegates in the committee
        """
        return [
            delegate for delegate in self._delegates.values()
            if delegate.committee.lower() == committee.lower()
        ]
    
    def get_delegates_by_country(self, country: str) -> List[Delegate]:
        """
        Get all delegates from a specific country
        
        Args:
            country: Country name
            
        Returns:
            List of delegates from the country
        """
        return [
            delegate for delegate in self._delegates.values()
            if delegate.country.lower() == country.lower()
        ]
    
    def get_delegates_with_pending_forms(self) -> List[Delegate]:
        """
        Get delegates with pending forms
        
        Returns:
            List of delegates with incomplete forms
        """
        return [
            delegate for delegate in self._delegates.values()
            if not delegate.is_forms_complete()
        ]


class AttendanceService:
    """
    Handles attendance tracking and related business logic
    
    This service manages attendance records, provides attendance
    statistics, and enforces attendance-related business rules.
    """
    
    def __init__(self):
        """Initialize attendance service"""
        self._attendance_log: Dict[str, AttendanceRecord] = {}
    
    def mark_attendance(self, delegate_id: str, oc_id: str) -> AttendanceRecord:
        """
        Mark delegate as present
        
        Args:
            delegate_id: ID of the delegate
            oc_id: ID of the OC member marking attendance
            
        Returns:
            AttendanceRecord instance
            
        Raises:
            AttendanceException: If attendance marking fails
        """
        if not delegate_id or not oc_id:
            raise AttendanceException(
                delegate_id, 
                "mark", 
                "Delegate ID and OC ID are required"
            )
        
        if delegate_id in self._attendance_log:
            # Already marked - return existing record
            return self._attendance_log[delegate_id]
        
        try:
            record = AttendanceRecord.create_new(delegate_id, oc_id)
            self._attendance_log[delegate_id] = record
            return record
            
        except Exception as e:
            raise AttendanceException(
                delegate_id, 
                "mark", 
                f"Failed to create attendance record: {str(e)}"
            )
    
    def get_attendance_record(self, delegate_id: str) -> Optional[AttendanceRecord]:
        """
        Get attendance record for delegate
        
        Args:
            delegate_id: Delegate ID
            
        Returns:
            AttendanceRecord or None if not found
        """
        return self._attendance_log.get(delegate_id)
    
    def is_present(self, delegate_id: str) -> bool:
        """
        Check if delegate is marked as present
        
        Args:
            delegate_id: Delegate ID
            
        Returns:
            True if delegate is present
        """
        return delegate_id in self._attendance_log
    
    def remove_attendance(self, delegate_id: str) -> bool:
        """
        Remove attendance record for delegate
        
        Args:
            delegate_id: Delegate ID
            
        Returns:
            True if record was removed, False if not found
        """
        if delegate_id in self._attendance_log:
            del self._attendance_log[delegate_id]
            return True
        return False
    
    def get_attendance_summary(self) -> Dict:
        """
        Get comprehensive attendance summary
        
        Returns:
            Dictionary with attendance statistics and records
        """
        records = list(self._attendance_log.values())
        
        # Count by OC member
        oc_counts = {}
        for record in records:
            oc_counts[record.scanned_by] = oc_counts.get(record.scanned_by, 0) + 1
        
        return {
            'total_scanned': len(self._attendance_log),
            'records': [record.to_dict() for record in records],
            'scanned_by_oc': oc_counts,
            'present_delegate_ids': list(self._attendance_log.keys())
        }
    
    def get_present_delegates(self) -> List[str]:
        """
        Get list of present delegate IDs
        
        Returns:
            List of delegate IDs that are marked present
        """
        return list(self._attendance_log.keys())
    
    def clear_all_attendance(self) -> int:
        """
        Clear all attendance records
        
        Returns:
            Number of records that were cleared
        """
        count = len(self._attendance_log)
        self._attendance_log.clear()
        return count
