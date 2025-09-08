from flask import Flask, request, render_template, redirect, url_for, session
import json
import time
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

# Data Models
class FormStatus(Enum):
    SUBMITTED = "Submitted"
    PENDING = "Pending"
    NOT_SUBMITTED = "Not Submitted"

@dataclass
class Delegate:
    """Data model for delegate information"""
    delegate_id: str
    name: str
    country: str
    committee: str
    liability_form: FormStatus
    transport_form: FormStatus
    
    @classmethod
    def from_dict(cls, delegate_id: str, data: Dict) -> 'Delegate':
        """Create Delegate instance from dictionary data"""
        return cls(
            delegate_id=delegate_id,
            name=data['name'],
            country=data['country'],
            committee=data['committee'],
            liability_form=FormStatus(data['liability_form']),
            transport_form=FormStatus(data['transport_form'])
        )
    
    def to_dict(self) -> Dict:
        """Convert delegate to dictionary for JSON serialization"""
        data = asdict(self)
        data['liability_form'] = self.liability_form.value
        data['transport_form'] = self.transport_form.value
        return data

@dataclass
class AttendanceRecord:
    """Data model for attendance tracking"""
    delegate_id: str
    scanned_by: str
    timestamp: str
    
    @classmethod
    def create_new(cls, delegate_id: str, oc_id: str) -> 'AttendanceRecord':
        """Create new attendance record with current timestamp"""
        return cls(
            delegate_id=delegate_id,
            scanned_by=oc_id,
            timestamp=time.ctime()
        )

@dataclass
class OrganizingCommittee:
    """Data model for OC member"""
    oc_id: str
    password: str
    
    def verify_password(self, password: str) -> bool:
        """Verify OC password"""
        return self.password == password

# Repository Pattern for Data Access
class DataRepository(ABC):
    """Abstract base class for data repositories"""
    
    @abstractmethod
    def load_data(self) -> Dict:
        pass
    
    @abstractmethod
    def save_data(self, data: Dict) -> None:
        pass

class JSONRepository(DataRepository):
    """JSON file-based repository implementation"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load_data(self) -> Dict:
        """Load data from JSON file"""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.file_path}: {e}")
    
    def save_data(self, data: Dict) -> None:
        """Save data to JSON file"""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

# Service Classes
class AuthenticationService:
    """Handles authentication logic"""
    
    def __init__(self, oc_repository: DataRepository):
        self.oc_repository = oc_repository
        self._oc_members: Dict[str, OrganizingCommittee] = {}
        self._load_oc_members()
    
    def _load_oc_members(self) -> None:
        """Load OC members from repository"""
        oc_data = self.oc_repository.load_data()
        self._oc_members = {
            oc_id: OrganizingCommittee(oc_id, password)
            for oc_id, password in oc_data.items()
        }
    
    def authenticate(self, oc_id: str, password: str) -> bool:
        """Authenticate OC member"""
        if oc_id not in self._oc_members:
            return False
        return self._oc_members[oc_id].verify_password(password)
    
    def get_oc_member(self, oc_id: str) -> Optional[OrganizingCommittee]:
        """Get OC member by ID"""
        return self._oc_members.get(oc_id)

class DelegateService:
    """Handles delegate-related operations"""
    
    def __init__(self, delegate_repository: DataRepository):
        self.delegate_repository = delegate_repository
        self._delegates: Dict[str, Delegate] = {}
        self._load_delegates()
    
    def _load_delegates(self) -> None:
        """Load delegates from repository"""
        delegate_data = self.delegate_repository.load_data()
        self._delegates = {
            delegate_id: Delegate.from_dict(delegate_id, data)
            for delegate_id, data in delegate_data.items()
        }
    
    def get_delegate(self, delegate_id: str) -> Optional[Delegate]:
        """Get delegate by ID"""
        return self._delegates.get(delegate_id)
    
    def get_all_delegates(self) -> List[Delegate]:
        """Get all delegates"""
        return list(self._delegates.values())
    
    def delegate_exists(self, delegate_id: str) -> bool:
        """Check if delegate exists"""
        return delegate_id in self._delegates

class AttendanceService:
    """Handles attendance tracking"""
    
    def __init__(self):
        self._attendance_log: Dict[str, AttendanceRecord] = {}
    
    def mark_attendance(self, delegate_id: str, oc_id: str) -> AttendanceRecord:
        """Mark delegate as present"""
        if delegate_id not in self._attendance_log:
            record = AttendanceRecord.create_new(delegate_id, oc_id)
            self._attendance_log[delegate_id] = record
            return record
        return self._attendance_log[delegate_id]
    
    def get_attendance_record(self, delegate_id: str) -> Optional[AttendanceRecord]:
        """Get attendance record for delegate"""
        return self._attendance_log.get(delegate_id)
    
    def is_present(self, delegate_id: str) -> bool:
        """Check if delegate is marked as present"""
        return delegate_id in self._attendance_log
    
    def get_attendance_summary(self) -> Dict:
        """Get attendance summary statistics"""
        return {
            'total_scanned': len(self._attendance_log),
            'records': [asdict(record) for record in self._attendance_log.values()]
        }

# Exception Classes
class MUNScannerException(Exception):
    """Base exception for MUN Scanner application"""
    pass

class DelegateNotFoundException(MUNScannerException):
    """Raised when delegate is not found"""
    pass

class AuthenticationFailedException(MUNScannerException):
    """Raised when authentication fails"""
    pass

# Main Application Class
class MUNScannerApp:
    """Main application class that orchestrates all services"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "MUN2025"
        self.app.permanent_session_lifetime = timedelta(days=1)
        
        # Initialize repositories
        self.oc_repository = JSONRepository("oc_list.json")
        self.delegate_repository = JSONRepository("delegates.json")
        
        # Initialize services
        self.auth_service = AuthenticationService(self.oc_repository)
        self.delegate_service = DelegateService(self.delegate_repository)
        self.attendance_service = AttendanceService()
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self) -> None:
        """Register Flask routes"""
        self.app.add_url_rule("/", "home", self.home)
        self.app.add_url_rule("/login", "login", self.login, methods=["GET", "POST"])
        self.app.add_url_rule("/logout", "logout", self.logout)
        self.app.add_url_rule("/scan/<delegate_id>", "scan", self.scan)
        self.app.add_url_rule("/validate/<delegate_id>", "validate", self.validate, methods=["POST"])
    
    def home(self):
        """Home page route"""
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        return render_template(
            "home.html",
            oc_id=session["oc_id"],
            delegate=None,
            delegate_id=None
        )
    
    def login(self):
        """Login route"""
        error = None
        if request.method == "POST":
            oc_id = request.form.get("oc_id")
            password = request.form.get("password")
            
            try:
                if self.auth_service.authenticate(oc_id, password):
                    session.permanent = True
                    session["oc_id"] = oc_id
                    return redirect(url_for("home"))
                else:
                    error = "Invalid Credentials"
            except Exception as e:
                error = "Authentication error occurred"
        
        return render_template("login.html", error=error)
    
    def logout(self):
        """Logout route"""
        session.pop("oc_id", None)
        return redirect(url_for("login"))
    
    def scan(self, delegate_id: str):
        """Scan delegate route"""
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        try:
            delegate = self.delegate_service.get_delegate(delegate_id)
            if not delegate:
                raise DelegateNotFoundException(f"Delegate {delegate_id} not found")
            
            # Prepare delegate data for template
            scanned_delegate = delegate.to_dict()
            
            # Add attendance information
            attendance_record = self.attendance_service.get_attendance_record(delegate_id)
            if attendance_record:
                scanned_delegate["scanned_by"] = attendance_record.scanned_by
                scanned_delegate["timestamp"] = attendance_record.timestamp
            else:
                scanned_delegate["scanned_by"] = None
                scanned_delegate["timestamp"] = None
            
            return render_template(
                "home.html",
                oc_id=session["oc_id"],
                delegate=scanned_delegate,
                delegate_id=delegate_id
            )
            
        except DelegateNotFoundException:
            return f"❌ Delegate {delegate_id} not found."
        except Exception as e:
            return f"❌ Error occurred: {str(e)}"
    
    def validate(self, delegate_id: str):
        """Validate attendance route"""
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        try:
            if not self.delegate_service.delegate_exists(delegate_id):
                raise DelegateNotFoundException(f"Delegate {delegate_id} does not exist")
            
            # Mark attendance
            self.attendance_service.mark_attendance(delegate_id, session["oc_id"])
            
            return redirect(url_for("scan", delegate_id=delegate_id))
            
        except DelegateNotFoundException:
            return f"❌ Delegate {delegate_id} does not exist"
        except Exception as e:
            return f"❌ Error occurred: {str(e)}"
    
    def _is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return "oc_id" in session
    
    def run(self, debug: bool = True) -> None:
        """Run the Flask application"""
        self.app.run(debug=debug)

# Factory function for creating the app
def create_app() -> MUNScannerApp:
    """Factory function to create and configure the application"""
    return MUNScannerApp()

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
