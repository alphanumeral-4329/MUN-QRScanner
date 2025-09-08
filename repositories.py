"""
Data Repository Classes for MUN Scanner Application

This module implements the Repository pattern for data access operations.
It provides an abstraction layer between the business logic and data storage,
making it easy to switch between different storage mechanisms.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional
from exceptions import DataAccessException


class DataRepository(ABC):
    """
    Abstract base class for data repositories
    
    This class defines the interface that all data repositories
    must implement, following the Repository pattern.
    """
    
    @abstractmethod
    def load_data(self) -> Dict:
        """
        Load data from the storage medium
        
        Returns:
            Dictionary containing the loaded data
            
        Raises:
            DataAccessException: If data loading fails
        """
        pass
    
    @abstractmethod
    def save_data(self, data: Dict) -> None:
        """
        Save data to the storage medium
        
        Args:
            data: Dictionary containing data to save
            
        Raises:
            DataAccessException: If data saving fails
        """
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """
        Check if the data source exists
        
        Returns:
            True if the data source exists, False otherwise
        """
        pass


class JSONRepository(DataRepository):
    """
    JSON file-based repository implementation
    
    This class provides data persistence using JSON files,
    with proper error handling and validation.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize JSON repository
        
        Args:
            file_path: Path to the JSON file
        """
        self.file_path = file_path
    
    def load_data(self) -> Dict:
        """
        Load data from JSON file
        
        Returns:
            Dictionary containing the loaded data
            
        Raises:
            DataAccessException: If file reading or JSON parsing fails
        """
        try:
            if not self.exists():
                return {}
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise DataAccessException(
                "read", 
                f"Invalid JSON in {self.file_path}: {str(e)}"
            )
        except PermissionError as e:
            raise DataAccessException(
                "read", 
                f"Permission denied accessing {self.file_path}: {str(e)}"
            )
        except Exception as e:
            raise DataAccessException(
                "read", 
                f"Unexpected error reading {self.file_path}: {str(e)}"
            )
    
    def save_data(self, data: Dict) -> None:
        """
        Save data to JSON file
        
        Args:
            data: Dictionary containing data to save
            
        Raises:
            DataAccessException: If file writing fails
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except PermissionError as e:
            raise DataAccessException(
                "write", 
                f"Permission denied writing to {self.file_path}: {str(e)}"
            )
        except json.JSONEncodeError as e:
            raise DataAccessException(
                "write", 
                f"JSON encoding error: {str(e)}"
            )
        except Exception as e:
            raise DataAccessException(
                "write", 
                f"Unexpected error writing to {self.file_path}: {str(e)}"
            )
    
    def exists(self) -> bool:
        """
        Check if the JSON file exists
        
        Returns:
            True if the file exists, False otherwise
        """
        return os.path.exists(self.file_path)
    
    def backup(self, backup_path: Optional[str] = None) -> str:
        """
        Create a backup of the current data file
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            Path to the backup file
            
        Raises:
            DataAccessException: If backup creation fails
        """
        if not self.exists():
            raise DataAccessException("backup", "Source file does not exist")
        
        if backup_path is None:
            backup_path = f"{self.file_path}.backup"
        
        try:
            data = self.load_data()
            backup_repo = JSONRepository(backup_path)
            backup_repo.save_data(data)
            return backup_path
            
        except Exception as e:
            raise DataAccessException(
                "backup", 
                f"Failed to create backup: {str(e)}"
            )


class InMemoryRepository(DataRepository):
    """
    In-memory repository implementation for testing
    
    This class provides a simple in-memory storage mechanism,
    useful for unit testing and development.
    """
    
    def __init__(self, initial_data: Optional[Dict] = None):
        """
        Initialize in-memory repository
        
        Args:
            initial_data: Optional initial data to store
        """
        self._data = initial_data or {}
    
    def load_data(self) -> Dict:
        """
        Load data from memory
        
        Returns:
            Dictionary containing the stored data
        """
        return self._data.copy()
    
    def save_data(self, data: Dict) -> None:
        """
        Save data to memory
        
        Args:
            data: Dictionary containing data to save
        """
        self._data = data.copy()
    
    def exists(self) -> bool:
        """
        Check if data exists in memory
        
        Returns:
            True if data exists, False otherwise
        """
        return bool(self._data)
    
    def clear(self) -> None:
        """Clear all data from memory"""
        self._data.clear()


class RepositoryFactory:
    """
    Factory class for creating repository instances
    
    This class provides a centralized way to create different
    types of repositories based on configuration.
    """
    
    @staticmethod
    def create_json_repository(file_path: str) -> JSONRepository:
        """
        Create a JSON repository instance
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            JSONRepository instance
        """
        return JSONRepository(file_path)
    
    @staticmethod
    def create_memory_repository(initial_data: Optional[Dict] = None) -> InMemoryRepository:
        """
        Create an in-memory repository instance
        
        Args:
            initial_data: Optional initial data
            
        Returns:
            InMemoryRepository instance
        """
        return InMemoryRepository(initial_data)
    
    @staticmethod
    def create_repository(repo_type: str, **kwargs) -> DataRepository:
        """
        Create a repository based on type
        
        Args:
            repo_type: Type of repository ('json' or 'memory')
            **kwargs: Additional arguments for repository creation
            
        Returns:
            DataRepository instance
            
        Raises:
            ValueError: If repository type is not supported
        """
        if repo_type.lower() == 'json':
            if 'file_path' not in kwargs:
                raise ValueError("file_path is required for JSON repository")
            return RepositoryFactory.create_json_repository(kwargs['file_path'])
        
        elif repo_type.lower() == 'memory':
            return RepositoryFactory.create_memory_repository(
                kwargs.get('initial_data')
            )
        
        else:
            raise ValueError(f"Unsupported repository type: {repo_type}")
