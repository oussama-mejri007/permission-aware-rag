
from getpass import getpass

from app.database import SessionLocal
from app.models.models import User
from app.auth import password_hash

password = getpass("Nouveau mot de passe : ")
confirmation = getpass("Confirmer le mot de passe : ")

if not password or password != confirmation:
    raise SystemExit("Mot de passe vide ou confirmations différentes.")

db = SessionLocal()

try:
    user = db.query(User).filter(
        User.email == "alice@company-a.com"
    ).first()

    if user is None:
        raise SystemExit("Utilisateur Alice introuvable.")

    user.password_hash = password_hash.hash(password)
    db.commit()
    print("Mot de passe Alice mis à jour.")
except Exception:
    db.rollback()
    raise
finally:
    db.close()
