import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.begin() as conn:
        # Cek kolom is_admin
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_admin'
        """))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
            print("Column is_admin added!")
        else:
            print("Column is_admin already exists")
        
        # Cek kolom is_deleted
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_deleted'
        """))
        if not result.fetchone():
            await conn.execute(text("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
            print("Column is_deleted added!")
        else:
            print("Column is_deleted already exists")
        
        # Set user id=1 sebagai admin
        await conn.execute(text("UPDATE users SET is_admin = TRUE WHERE id = 1"))
        print("User id=1 is now admin")

if __name__ == "__main__":
    asyncio.run(main())
