"""
Main Application Module for MUN Scanner

This module contains the main Flask application class that orchestrates
all services and handles HTTP requests. It serves as the entry point
for the MUN Scanner web application.
"""

from flask import Flask, request, render_template, redirect, url_for, session
from datetime import timedelta
from typing import Optional

from repositories import RepositoryFactory
from services import AuthenticationService, DelegateService, AttendanceService
from exceptions import (
    MUNScannerException,
    DelegateNotFoundException, 
    AuthenticationFailedException,
    AttendanceException
)


class MUNScannerApp:
    """
    Main Flask application class for MUN Scanner
    
    This class orchestrates all services and handles the web interface
    for the Model UN delegate scanning system.
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the MUN Scanner application
        
        Args:
            config: Optional configuration dictionary
        """
        # Initialize Flask app
        self.app = Flask(__name__)
        self._configure_app(config)
        
        # Initialize repositories
        self.oc_repository = RepositoryFactory.create_json_repository("oc_list.json")
        self.delegate_repository = RepositoryFactory.create_json_repository("delegates.json")
        
        # Initialize services
        self.auth_service = AuthenticationService(self.oc_repository)
        self.delegate_service = DelegateService(self.delegate_repository)
        self.attendance_service = AttendanceService()
        
        # Register routes
        self._register_routes()
        
        # Register error handlers
        self._register_error_handlers()
    
    def _configure_app(self, config: Optional[dict] = None) -> None:
        """
        Configure Flask application settings
        
        Args:
            config: Optional configuration dictionary
        """
        # Default configuration
        default_config = {
            'SECRET_KEY': 'MUN2025',
            'PERMANENT_SESSION_LIFETIME': timedelta(days=1),
            'DEBUG': True
        }
        
        # Update with provided config
        if config:
            default_config.update(config)
        
        # Apply configuration
        self.app.secret_key = default_config['SECRET_KEY']
        self.app.permanent_session_lifetime = default_config['PERMANENT_SESSION_LIFETIME']
        self.app.config['DEBUG'] = default_config['DEBUG']
    
    def _register_routes(self) -> None:
        """Register all Flask routes"""
        self.app.add_url_rule("/", "home", self.home)
        self.app.add_url_rule("/login", "login", self.login, methods=["GET", "POST"])
        self.app.add_url_rule("/logout", "logout", self.logout)
        self.app.add_url_rule("/scan/<delegate_id>", "scan", self.scan)
        self.app.add_url_rule("/validate/<delegate_id>", "validate", self.validate, methods=["POST"])
        
        # Additional routes for enhanced functionality
        self.app.add_url_rule("/dashboard", "dashboard", self.dashboard)
        self.app.add_url_rule("/attendance/summary", "attendance_summary", self.attendance_summary)
    
    def _register_error_handlers(self) -> None:
        """Register error handlers for custom exceptions"""
        
        @self.app.errorhandler(DelegateNotFoundException)
        def handle_delegate_not_found(e):
            return render_template('error.html', 
                                 error_title="Delegate Not Found",
                                 error_message=str(e)), 404
        
        @self.app.errorhandler(AuthenticationFailedException)
        def handle_auth_failed(e):
            return render_template('login.html', 
                                 error="Authentication failed. Please check your credentials."), 401
        
        @self.app.errorhandler(MUNScannerException)
        def handle_mun_scanner_exception(e):
            return render_template('error.html',
                                 error_title="Application Error",
                                 error_message=str(e)), 500
    
    def home(self):
        """
        Home page route
        
        Returns:
            Rendered home template or redirect to login
        """
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        return render_template(
            "home.html",
            oc_id=session["oc_id"],
            delegate=None,
            delegate_id=None
        )
    
    def login(self):
        """
        Login route for OC member authentication
        
        Returns:
            Rendered login template or redirect to home on success
        """
        error = None
        
        if request.method == "POST":
            oc_id = request.form.get("oc_id", "").strip()
            password = request.form.get("password", "").strip()
            
            try:
                if self.auth_service.authenticate(oc_id, password):
                    session.permanent = True
                    session["oc_id"] = oc_id
                    return redirect(url_for("home"))
                    
            except AuthenticationFailedException:
                error = "Invalid credentials. Please try again."
            except Exception as e:
                error = "An error occurred during login. Please try again."
                # Log the error in a real application
                print(f"Login error: {str(e)}")
        
        return render_template("login.html", error=error)
    
    def logout(self):
        """
        Logout route
        
        Returns:
            Redirect to login page
        """
        session.pop("oc_id", None)
        return redirect(url_for("login"))
    
    def scan(self, delegate_id: str):
        """
        Scan delegate route - displays delegate information
        
        Args:
            delegate_id: ID of the delegate to scan
            
        Returns:
            Rendered template with delegate information
        """
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        try:
            # Get delegate information
            delegate = self.delegate_service.get_delegate_or_raise(delegate_id)
            
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
            return f"❌ Delegate {delegate_id} not found.", 404
        except Exception as e:
            return f"❌ Error occurred: {str(e)}", 500
    
    def validate(self, delegate_id: str):
        """
        Validate attendance route - marks delegate as present
        
        Args:
            delegate_id: ID of the delegate to mark present
            
        Returns:
            Redirect to scan page with updated information
        """
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        try:
            # Verify delegate exists
            self.delegate_service.get_delegate_or_raise(delegate_id)
            
            # Mark attendance
            self.attendance_service.mark_attendance(delegate_id, session["oc_id"])
            
            return redirect(url_for("scan", delegate_id=delegate_id))
            
        except DelegateNotFoundException:
            return f"❌ Delegate {delegate_id} does not exist", 404
        except AttendanceException as e:
            return f"❌ Attendance error: {str(e)}", 500
        except Exception as e:
            return f"❌ Error occurred: {str(e)}", 500
    
    def dashboard(self):
        """
        Dashboard route - shows application statistics
        
        Returns:
            Rendered dashboard template
        """
        if not self._is_authenticated():
            return redirect(url_for("login"))
        
        try:
            # Get statistics
            all_delegates = self.delegate_service.get_all_delegates()
            attendance_summary = self.attendance_service.get_attendance_summary()
            pending_forms = self.delegate_service.get_delegates_with_pending_forms()
            
            stats = {
                'total_delegates': len(all_delegates),
                'present_delegates': attendance_summary['total_scanned'],
                'pending_forms': len(pending_forms),
                'attendance_rate': (attendance_summary['total_scanned'] / len(all_delegates) * 100) if all_delegates else 0
            }
            
            return render_template(
                "dashboard.html",
                oc_id=session["oc_id"],
                stats=stats,
                attendance_summary=attendance_summary
            )
            
        except Exception as e:
            return f"❌ Error loading dashboard: {str(e)}", 500
    
    def attendance_summary(self):
        """
        Attendance summary route - detailed attendance information
        
        Returns:
            JSON response with attendance data
        """
        if not self._is_authenticated():
            return {"error": "Authentication required"}, 401
        
        try:
            summary = self.attendance_service.get_attendance_summary()
            return summary
            
        except Exception as e:
            return {"error": f"Failed to get attendance summary: {str(e)}"}, 500
    
    def _is_authenticated(self) -> bool:
        """
        Check if current user is authenticated
        
        Returns:
            True if user is authenticated
        """
        oc_id = session.get("oc_id")
        if not oc_id:
            return False
        
        # Verify OC ID is still valid
        return self.auth_service.is_valid_oc_id(oc_id)
    
    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = None) -> None:
        """
        Run the Flask application
        
        Args:
            host: Host address to bind to
            port: Port number to listen on
            debug: Debug mode (overrides config if provided)
        """
        if debug is not None:
            self.app.config['DEBUG'] = debug
        
        self.app.run(host=host, port=port, debug=self.app.config['DEBUG'])


def create_app(config: Optional[dict] = None) -> MUNScannerApp:
    """
    Factory function to create and configure the application
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured MUNScannerApp instance
    """
    return MUNScannerApp(config)


def create_development_app() -> MUNScannerApp:
    """
    Create application configured for development
    
    Returns:
        MUNScannerApp configured for development
    """
    dev_config = {
        'DEBUG': True,
        'SECRET_KEY': 'dev-secret-key-change-in-production'
    }
    return create_app(dev_config)


def create_production_app() -> MUNScannerApp:
    """
    Create application configured for production
    
    Returns:
        MUNScannerApp configured for production
    """
    prod_config = {
        'DEBUG': False,
        'SECRET_KEY': 'production-secret-key-from-environment'
    }
    return create_app(prod_config)


if __name__ == "__main__":
    # Create and run the application
    app = create_development_app()
    app.run(debug=True)
