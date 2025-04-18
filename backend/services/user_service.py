from sqlalchemy import text
from sqlalchemy.orm import Session
from services import auth_service

def create_user(db: Session, user_data: dict):
    """Create a new user."""
    try:
        # Check if user already exists
        check_query = text("SELECT id FROM users WHERE username = :username OR email = :email")
        existing_user = db.execute(
            check_query, 
            {"username": user_data["username"], "email": user_data["email"]}
        ).fetchone()
        
        if existing_user:
            return None, "Username or email already registered"
        
        # Hash the password
        hashed_password = auth_service.get_password_hash(user_data["password"])
        
        # Insert user
        insert_query = text("""
        INSERT INTO users (
            username, email, full_name, hashed_password, 
            is_active, is_superuser, profile_image_url, job_title, bio, 
            created_at, updated_at
        ) 
        VALUES (
            :username, :email, :full_name, :hashed_password, 
            :is_active, :is_superuser, :profile_image_url, :job_title, :bio,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        RETURNING id, username, email, full_name, is_active, is_superuser, profile_image_url, job_title, bio
        """)
        
        result = db.execute(
            insert_query, 
            {
                "username": user_data["username"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "hashed_password": hashed_password,
                "is_active": user_data.get("is_active", True),
                "is_superuser": user_data.get("is_superuser", False),
                "profile_image_url": user_data.get("profile_image_url"),
                "job_title": user_data.get("job_title"),
                "bio": user_data.get("bio")
            }
        ).fetchone()
        
        db.commit()
        
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5],
            "profile_image_url": result[6],
            "job_title": result[7],
            "bio": result[8]
        }, None
    
    except Exception as e:
        db.rollback()
        return None, f"Error creating user: {str(e)}"

def get_user_by_id(db: Session, user_id: int):
    """Get a user by ID."""
    query = text("""
    SELECT 
        id, username, email, full_name, is_active, is_superuser, 
        profile_image_url, job_title, bio, created_at, updated_at
    FROM users 
    WHERE id = :id
    """)
    result = db.execute(query, {"id": user_id}).fetchone()
    
    if not result:
        return None
        
    return {
        "id": result[0],
        "username": result[1],
        "email": result[2],
        "full_name": result[3],
        "is_active": result[4],
        "is_superuser": result[5],
        "profile_image_url": result[6],
        "job_title": result[7],
        "bio": result[8],
        "created_at": result[9],
        "updated_at": result[10]
    }

def get_user_by_username(db: Session, username: str):
    """Get a user by username."""
    query = text("""
    SELECT 
        id, username, email, full_name, is_active, is_superuser, 
        profile_image_url, job_title, bio, created_at, updated_at
    FROM users 
    WHERE username = :username
    """)
    result = db.execute(query, {"username": username}).fetchone()
    
    if not result:
        return None
        
    return {
        "id": result[0],
        "username": result[1],
        "email": result[2],
        "full_name": result[3],
        "is_active": result[4],
        "is_superuser": result[5],
        "profile_image_url": result[6],
        "job_title": result[7],
        "bio": result[8],
        "created_at": result[9],
        "updated_at": result[10]
    }

def get_user_by_email(db: Session, email: str):
    """Get a user by email."""
    query = text("""
    SELECT 
        id, username, email, full_name, is_active, is_superuser, 
        profile_image_url, job_title, bio, created_at, updated_at
    FROM users 
    WHERE email = :email
    """)
    result = db.execute(query, {"email": email}).fetchone()
    
    if not result:
        return None
        
    return {
        "id": result[0],
        "username": result[1],
        "email": result[2],
        "full_name": result[3],
        "is_active": result[4],
        "is_superuser": result[5],
        "profile_image_url": result[6],
        "job_title": result[7],
        "bio": result[8],
        "created_at": result[9],
        "updated_at": result[10]
    }

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users."""
    query = text("""
    SELECT 
        id, username, email, full_name, is_active, is_superuser, 
        profile_image_url, job_title, bio
    FROM users
    ORDER BY id
    LIMIT :limit OFFSET :skip
    """)
    
    results = db.execute(query, {"limit": limit, "skip": skip}).fetchall()
    
    users = []
    for row in results:
        users.append({
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "full_name": row[3],
            "is_active": row[4],
            "is_superuser": row[5],
            "profile_image_url": row[6],
            "job_title": row[7],
            "bio": row[8]
        })
    
    return users

def update_user(db: Session, user_id: int, user_data: dict):
    """Update a user."""
    try:
        # Check if user exists
        user = get_user_by_id(db, user_id)
        
        if not user:
            return None, "User not found"
        
        # Build update query dynamically
        update_fields = []
        params = {"id": user_id}
        
        # Regular user fields
        if "email" in user_data and user_data["email"] is not None:
            update_fields.append("email = :email")
            params["email"] = user_data["email"]
            
        if "full_name" in user_data and user_data["full_name"] is not None:
            update_fields.append("full_name = :full_name")
            params["full_name"] = user_data["full_name"]
            
        if "profile_image_url" in user_data and user_data["profile_image_url"] is not None:
            update_fields.append("profile_image_url = :profile_image_url")
            params["profile_image_url"] = user_data["profile_image_url"]
            
        if "job_title" in user_data and user_data["job_title"] is not None:
            update_fields.append("job_title = :job_title")
            params["job_title"] = user_data["job_title"]
            
        if "bio" in user_data and user_data["bio"] is not None:
            update_fields.append("bio = :bio")
            params["bio"] = user_data["bio"]
            
        # Admin-only fields
        if "is_active" in user_data and user_data["is_active"] is not None:
            update_fields.append("is_active = :is_active")
            params["is_active"] = user_data["is_active"]
            
        if "is_superuser" in user_data and user_data["is_superuser"] is not None:
            update_fields.append("is_superuser = :is_superuser")
            params["is_superuser"] = user_data["is_superuser"]
            
        # Password update
        if "password" in user_data and user_data["password"] is not None:
            hashed_password = auth_service.get_password_hash(user_data["password"])
            update_fields.append("hashed_password = :hashed_password")
            params["hashed_password"] = hashed_password
        
        if not update_fields:
            return user, None
            
        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build and execute update query
        update_query = text(f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = :id
            RETURNING id, username, email, full_name, is_active, is_superuser, 
                     profile_image_url, job_title, bio
        """)
        
        result = db.execute(update_query, params).fetchone()
        db.commit()
        
        if not result:
            return None, "Failed to update user"
            
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5],
            "profile_image_url": result[6],
            "job_title": result[7],
            "bio": result[8]
        }, None
        
    except Exception as e:
        db.rollback()
        return None, f"Error updating user: {str(e)}"

def delete_user(db: Session, user_id: int) -> str:
    """Delete a user."""
    try:
        # Check if user exists
        user = get_user_by_id(db, user_id)
        if not user:
            return "User not found"
            
        # Delete user
        delete_query = text("DELETE FROM users WHERE id = :id")
        db.execute(delete_query, {"id": user_id})
        db.commit()
        
        return None
        
    except Exception as e:
        db.rollback()
        return f"Error deleting user: {str(e)}"

def activate_user(db: Session, user_id: int):
    """Activate a user."""
    return update_user(db, user_id, {"is_active": True})

def deactivate_user(db: Session, user_id: int):
    """Deactivate a user."""
    return update_user(db, user_id, {"is_active": False})

def set_user_superuser_status(db: Session, user_id: int, is_superuser: bool):
    """Set user superuser status."""
    return update_user(db, user_id, {"is_superuser": is_superuser})

def update_user_profile(db: Session, user_id: int, update_data: dict):
    """Update a user's profile with proper validation."""
    try:
        # Check if user exists
        user = get_user_by_id(db, user_id)
        if not user:
            return None, "User not found"

        # Check if username is being changed and if it's already taken
        if "username" in update_data and update_data["username"]:
            existing_user = get_user_by_username(db, update_data["username"])
            if existing_user and existing_user["id"] != user_id:
                return None, "Username already taken"

        # Check if email is being changed and if it's already taken
        if "email" in update_data and update_data["email"]:
            existing_user = get_user_by_email(db, update_data["email"])
            if existing_user and existing_user["id"] != user_id:
                return None, "Email already taken"

        # Handle password change if requested
        if "password" in update_data and update_data["password"]:
            if "current_password" not in update_data or not update_data["current_password"]:
                return None, "Current password is required to change password"
            
            # Verify current password
            if not auth_service.verify_password(update_data["current_password"], user["hashed_password"]):
                return None, "Current password is incorrect"
            
            # Hash new password
            update_data["hashed_password"] = auth_service.get_password_hash(update_data["password"])
            del update_data["password"]
            del update_data["current_password"]

        # Build update query
        update_fields = []
        params = {"id": user_id}
        
        for field in ["username", "email", "full_name", "hashed_password", "profile_image_url", "job_title", "bio"]:
            if field in update_data and update_data[field] is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = update_data[field]

        if not update_fields:
            return None, "No fields to update"

        # Add updated_at timestamp
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        # Execute update
        update_query = text(f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE id = :id
            RETURNING id, username, email, full_name, is_active, is_superuser, 
                     profile_image_url, job_title, bio
        """)

        result = db.execute(update_query, params).fetchone()
        db.commit()

        if not result:
            return None, "Failed to update user"

        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "full_name": result[3],
            "is_active": result[4],
            "is_superuser": result[5],
            "profile_image_url": result[6],
            "job_title": result[7],
            "bio": result[8]
        }, None

    except Exception as e:
        db.rollback()
        return None, f"Error updating profile: {str(e)}" 