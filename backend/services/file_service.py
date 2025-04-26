import os
import uuid
from fastapi import UploadFile
from typing import Tuple, Union


class FileService:
    def __init__(self, upload_dir: str = "uploads/tasks"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        # Create a general folder for files not associated with tasks
        general_dir = os.path.join(self.upload_dir, "general")
        os.makedirs(general_dir, exist_ok=True)

    async def save_file(self, file: UploadFile, task_id: Union[int, str]) -> Tuple[str, str, int]:
        """
        Save an uploaded file to disk
        
        Args:
            file: The uploaded file
            task_id: The ID of the task the file is attached to, or 'general' for standalone files
            
        Returns:
            Tuple containing (unique_filename, file_path, file_size)
        """
        # Create a unique filename to avoid collisions
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Create appropriate directory if it doesn't exist
        folder_name = f"task_{task_id}" if isinstance(task_id, int) else str(task_id)
        task_dir = os.path.join(self.upload_dir, folder_name)
        os.makedirs(task_dir, exist_ok=True)
        
        # Define the file path
        file_path = os.path.join(task_dir, unique_filename)
        
        # Read and save the file content
        file_content = await file.read()
        file_size = len(file_content)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        return unique_filename, file_path, file_size
        
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk
        
        Args:
            file_path: The path to the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False 