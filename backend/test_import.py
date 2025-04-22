# Simple test file to check imports
from crud import project as project_crud

# Print what methods are available
print("Available methods in project_crud:")
print(dir(project_crud))

# Check if create_with_owner exists
if hasattr(project_crud, 'create_with_owner'):
    print("✅ SUCCESS: create_with_owner method exists!")
else:
    print("❌ ERROR: create_with_owner method doesn't exist!")
    
    # Check if the class has the method
    if hasattr(project_crud.__class__, 'create_with_owner'):
        print("Method exists in the class but not in the instance")
    
# Print the full module path to ensure we're importing the right file
print(f"Project CRUD module file: {project_crud.__module__}") 