import hashlib

# UUID użytkownika z logów
user_uuid = "207222a2-3845-40c2-9bea-cd5bbd6e15f6"

# Deterministyczne hashowanie (NOWA metoda)
hash_bytes = hashlib.md5(user_uuid.encode('utf-8')).digest()
user_id_deterministic = int.from_bytes(hash_bytes[:4], byteorder='big')

print(f"UUID: {user_uuid}")
print(f"Deterministyczny user_id: {user_id_deterministic}")

# Powtórzmy dla weryfikacji
hash_bytes2 = hashlib.md5(user_uuid.encode('utf-8')).digest()
user_id_test = int.from_bytes(hash_bytes2[:4], byteorder='big')
print(f"Powtórzone hashowanie: {user_id_test}")
print(f"Czy takie samo? {user_id_deterministic == user_id_test}")
