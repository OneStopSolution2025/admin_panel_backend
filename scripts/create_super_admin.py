"""
Script to create initial Super Admin user.
Run this once during initial setup.
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.models import User, UserType
from app.core.security import security_manager
from app.services.wallet_service import WalletService
import sys


async def create_super_admin():
    """Create super admin user"""
    
    email = input("Enter Super Admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return
    
    password = input("Enter Super Admin password (min 8 chars): ").strip()
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return
    
    full_name = input("Enter Super Admin full name: ").strip()
    if not full_name:
        print("Error: Full name is required")
        return
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if super admin already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.user_type == UserType.SUPER_ADMIN)
            )
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                print(f"\nSuper Admin already exists: {existing_admin.email}")
                overwrite = input("Do you want to create another one? (yes/no): ").strip().lower()
                if overwrite != 'yes':
                    print("Operation cancelled")
                    return
            
            # Create super admin user
            admin = User(
                user_id="ADMIN-001",
                email=email,
                hashed_password=security_manager.get_password_hash(password),
                full_name=full_name,
                user_type=UserType.SUPER_ADMIN,
                is_active=True,
                is_blocked=False
            )
            
            session.add(admin)
            await session.flush()
            
            # Create wallet
            await WalletService.create_wallet(admin.id, session)
            
            await session.commit()
            await session.refresh(admin)
            
            print("\n" + "="*50)
            print("Super Admin Created Successfully!")
            print("="*50)
            print(f"User ID: {admin.user_id}")
            print(f"Email: {admin.email}")
            print(f"Name: {admin.full_name}")
            print(f"Type: {admin.user_type.value}")
            print("="*50)
            print("\nYou can now login with these credentials.")
            
        except Exception as e:
            await session.rollback()
            print(f"\nError creating super admin: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    print("\n" + "="*50)
    print("Super Admin Creation Script")
    print("="*50 + "\n")
    
    asyncio.run(create_super_admin())
