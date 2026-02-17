import sqlite3
import bcrypt

def create_user(username, password, role):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, password_hash, role)
    )

    conn.commit()
    conn.close()

    print(f"User '{username}' created with role '{role}'.")

# --------- HIER USER DEFINIEREN ---------

create_user("olestegk", "-", "child")
create_user("idastegk", "-", "child")
create_user("testuser", "-", "child")
create_user("eltern", "-", "parent")
create_user("admin", "-", "admin")
