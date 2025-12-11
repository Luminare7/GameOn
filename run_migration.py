"""Database migration runner for GameOn."""
import sqlite3
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

def ensure_database_exists(db_path: str):
    """Create database if it doesn't exist."""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"📁 Created directory: {db_dir}")
    
    if not os.path.exists(db_path):
        print(f"📝 Database not found. Creating: {db_path}")
        conn = sqlite3.connect(db_path)
        # Create basic structure (will be updated by migration)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        print(f"✅ Database created")
        return True
    return False

def backup_database(db_path: str):
    """Create a backup of the database."""
    # Check if database has content
    if os.path.getsize(db_path) == 0:
        print("💾 Skipping backup (database is empty)")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"💾 Database backed up to: {backup_path}")
    return backup_path

def run_migration(db_path: str, migration_file: str):
    """Run a migration SQL file."""
    print(f"📦 Running migration: {os.path.basename(migration_file)}")
    
    with open(migration_file, 'r') as f:
        sql_script = f.read()
    
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        print(f"✅ Migration completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_migration.py <path_to_database>")
        print("Example: python run_migration.py data/gameon.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    print("=" * 60)
    print("GameOn Database Migration")
    print("=" * 60)
    
    # Ensure database exists
    is_new = ensure_database_exists(db_path)
    
    # Backup existing database (if it has content)
    if not is_new:
        backup_path = backup_database(db_path)
    
    # Find and run migrations
    migrations_dir = Path(__file__).parent / 'migrations'
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    migration_files = sorted(migrations_dir.glob('*.sql'))
    
    if not migration_files:
        print("❌ No migration files found")
        sys.exit(1)
    
    print(f"\nFound {len(migration_files)} migration(s):")
    for mf in migration_files:
        print(f"  - {mf.name}")
    print()
    
    success = True
    for migration_file in migration_files:
        if not run_migration(db_path, str(migration_file)):
            success = False
            break
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All migrations completed successfully!")
        print("=" * 60)
        if is_new:
            print("\n💡 Database initialized and ready to use!")
        else:
            print("\n💡 Database upgraded successfully!")
    else:
        print("❌ Migration failed!")
        print("=" * 60)
        if not is_new and backup_path:
            print(f"\n🔄 To restore: cp {backup_path} {db_path}")
        sys.exit(1)

if __name__ == '__main__':
    main()