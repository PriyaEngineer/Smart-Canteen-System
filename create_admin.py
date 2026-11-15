from getpass import getpass
from werkzeug.security import generate_password_hash

password = getpass("Enter admin password: ")

hashed_password = generate_password_hash(password)

print("\nYour admin password hash:\n")
print(hashed_password)