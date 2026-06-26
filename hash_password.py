import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python hash_password.py <your_password>")
        sys.exit(1)
    
    try:
        import bcrypt
    except ImportError:
        print("Error: The 'bcrypt' library is not installed.")
        print("Please install it first: pip install bcrypt")
        sys.exit(1)
        
    password = sys.argv[1]
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    print("\n==================================================")
    print("Your secure bcrypt hashed password is:")
    print(hashed.decode('utf-8'))
    print("==================================================")
    print("\nCopy this hash and set it as APP_PASSWORD in your .env file.")
    print("Example:\nAPP_PASSWORD=" + hashed.decode('utf-8'))

if __name__ == "__main__":
    main()
