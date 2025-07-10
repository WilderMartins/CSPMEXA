from sqlalchemy.orm import Session
from typing import Optional

from app.models.user_model import User
from app.schemas.user_schema import UserCreate # Pode ser útil, ou criar um schema específico para OAuth
import logging

logger = logging.getLogger(__name__)

class UserService:
    def get_user_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_user_by_google_id(self, db: Session, *, google_id: str) -> Optional[User]:
        return db.query(User).filter(User.google_id == google_id).first()

    def create_user_oauth(
        self,
        db: Session,
        *,
        email: str,
        google_id: str,
        # Adicionar outros campos que vêm do Google e podem ser úteis
        # name: Optional[str] = None,
        # picture: Optional[str] = None
    ) -> User:
        logger.info(f"Creating new OAuth user for email: {email}, google_id: {google_id}")
        # Aqui, não estamos definindo uma senha local, pois é um login OAuth
        # is_active e is_superuser terão seus defaults do modelo User (True, False)
        db_user = User(
            email=email,
            google_id=google_id,
            # Adicionar outros campos aqui se necessário
            # full_name=name, # Se tiver um campo full_name no modelo User
            # profile_picture_url=picture, # Se tiver
            is_active=True, # Default, mas explícito
            is_superuser=False # Default, mas explícito
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def get_or_create_user_oauth(
        self,
        db: Session,
        *,
        email: str,
        google_id: str,
        # name: Optional[str] = None, # Opcional
        # picture: Optional[str] = None # Opcional
    ) -> User:
        user = self.get_user_by_google_id(db, google_id=google_id)
        if user:
            logger.info(f"User found by google_id: {google_id}")
            # Opcional: atualizar campos como nome/foto se mudaram no Google
            # if name and user.full_name != name: user.full_name = name
            # if picture and user.profile_picture_url != picture: user.profile_picture_url = picture
            # db.commit()
            # db.refresh(user)
            return user

        logger.info(f"User not found by google_id: {google_id}. Checking by email: {email}")
        user = self.get_user_by_email(db, email=email)
        if user:
            logger.info(f"User found by email: {email}. Associating google_id: {google_id}")
            if not user.google_id: # Associar google_id se não estiver definido
                user.google_id = google_id
                # Opcional: atualizar nome/foto aqui também
                db.commit()
                db.refresh(user)
            # Se o e-mail existe mas com um google_id diferente, é uma situação a ser tratada.
            # Poderia ser um erro, ou uma política de merge/link de contas.
            # Para o MVP, se o google_id do usuário encontrado não bate, podemos levantar um erro
            # ou simplesmente retornar o usuário (o que pode ser um risco de segurança se não tratado corretamente).
            # Por ora, se o email existe, e o google_id bate ou está vazio, atualizamos e retornamos.
            # Se o google_id existe e é diferente, isso é um caso mais complexo.
            # Vamos assumir que se o email é o mesmo, é o mesmo usuário.
            return user

        logger.info(f"No existing user found. Creating new user with google_id: {google_id} and email: {email}")
        return self.create_user_oauth(db, email=email, google_id=google_id) #, name=name, picture=picture)

    def enable_mfa(self, db: Session, *, user: User, mfa_secret: str) -> User:
        logger.info(f"Enabling MFA for user_id: {user.id}")
        user.mfa_secret = mfa_secret
        user.is_mfa_enabled = True
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def disable_mfa(self, db: Session, *, user: User) -> User:
        logger.info(f"Disabling MFA for user_id: {user.id}")
        user.mfa_secret = None
        user.is_mfa_enabled = False
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

user_service = UserService()
