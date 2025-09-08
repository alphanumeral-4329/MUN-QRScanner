"""
Data Models for MUN Scanner Application

This module contains all data model classes that represent the core entities
in the MUN Scanner system. These classes use dataclasses for clean, 
type-safe data representation.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict
import time


class FormStatus(Enum):
    """Enumeration for form submission status"""
    SUBMITTED = "Submitted"
    PENDING = "Pending"
    NOT_SUBMITTED = "Not Submitted"


@dataclass
class Delegate:
    """
    Data model for delegate information
    
    Represents a Model UN delegate with their personal information,
    committee assignment, and form submission status.
    """
    delegate_id: str
    name: str
    country: str
    committee: str
    liability_form: FormStatus
    transport_form: FormStatus
    
    @classmethod
    def from_dict(cls, delegate_id: str, data: Dict) -> 'Delegate':
        """
        Create Delegate instance from dictionary data
        
        Args:
            delegate_id: Unique identifier for the delegate
            data: Dictionary containing delegate information
            
        Returns:
            Delegate instance
        """
        return cls(
            delegate_id=delegate_id,
            name=data['name'],
            country=data['country'],
            committee=data['committee'],
            liability_form=FormStatus(data['liability_form']),
            transport_form=FormStatus(data['transport_form'])
        )
    
    def to_dict(self) -> Dict:
        """
        Convert delegate to dictionary for JSON serialization
        
        Returns:
            Dictionary representation of the delegate
        """
        data = asdict(self)
        data['liability_form'] = self.liability_form.value
        data['transport_form'] = self.transport_form.value
        return data
    
    def is_forms_complete(self) -> bool:
        """
        Check if all required forms are submitted
        
        Returns:
            True if both liability and transport forms are submitted
        """
        return (self.liability_form == FormStatus.SUBMITTED and 
                self.transport_form == FormStatus.SUBMITTED)


@dataclass
class AttendanceRecord:
    """
    Data model for attendance tracking
    
    Represents a single attendance record when a delegate
    is scanned by an organizing committee member.
    """
    delegate_id: str
    scanned_by: str
    timestamp: str
    
    @classmethod
    def create_new(cls, delegate_id: str, oc_id: str) -> 'AttendanceRecord':
        """
        Create new attendance record with current timestamp
        
        Args:
            delegate_id: ID of the delegate being scanned
            oc_id: ID of the OC member doing the scanning
            
        Returns:
            New AttendanceRecord instance
        """
        return cls(
            delegate_id=delegate_id,
            scanned_by=oc_id,
            timestamp=time.ctime()
        )
    
    def to_dict(self) -> Dict:
        """
        Convert attendance record to dictionary
        
        Returns:
            Dictionary representation of the attendance record
        """
        return asdict(self)


@dataclass
class OrganizingCommittee:
    """
    Data model for Organizing Committee member
    
    Represents an OC member with authentication capabilities.
    """
    oc_id: str
    password: str
    
    def verify_password(self, password: str) -> bool:
        """
        Verify OC member password
        
        Args:
            password: Password to verify
            
        Returns:
            True if password matches
        """
        return self.password == password
    
    def to_dict(self) -> Dict:
        """
        Convert OC member to dictionary (excluding password for security)
        
        Returns:
            Dictionary with OC ID only
        """
        return {"oc_id": self.oc_id}
