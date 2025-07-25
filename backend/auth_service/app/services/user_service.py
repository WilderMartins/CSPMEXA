from sqlalchemy.orm import Session
from typing import Optional
from app.services.audit_service_client import audit_service_client
from app.models.user_model import User
from app.schemas.user_schema import UserCreate, UserUpdateByAdmin
import logging

logger = logging.getLogger(__name__)

class UserService:
    def get_user_by_email(self, db: Session, *, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_user_by_google_id(self, db: Session, *, google_id: str) -> Optional[User]:
        return db.query(User).filter(User.google_id == google_id).first()

    async def create_user_oauth(
        self,
        db: Session,
        *,
        email: str,
        google_id: str,
        full_name: Optional[str] = None,
        profile_picture_url: Optional[str] = None
    ) -> User:
        logger.info(f"Creating new OAuth user for email: {email}, google_id: {google_id}")
        db_user = User(
            email=email,
            google_id=google_id,
            full_name=full_name,
            profile_picture_url=profile_picture_url,
            is_active=True,
            is_superuser=False,
            permissions=["run:analysis"]
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        try:
            await audit_service_client.create_event(
                actor="system",
                action="user_created",
                resource=f"user:{db_user.id}",
                details={"email": db_user.email, "google_id": db_user.google_id}
            )
        except Exception as e:
            logger.error(f"Falha ao enviar evento de auditoria para criação de usuário: {e}")

        return db_user

    async def get_or_create_user_oauth(
        self,
        db: Session,
        *,
        email: str,
        google_id: str,
        full_name: Optional[str] = None,
        profile_picture_url: Optional[str] = None
    ) -> User:
        # Esta função lida com a lógica de encontrar ou criar um usuário durante o fluxo OAuth.
        # A lógica é a seguinte:
        # 1. Tenta encontrar o usuário pelo google_id. Se encontrar, atualiza os dados e retorna o usuário.
        # 2. Se não encontrar pelo google_id, tenta encontrar pelo email.
        # 3. Se encontrar pelo email, associa o google_id à conta (se já não tiver um) e atualiza os dados.
        # 4. Se não encontrar por nenhum dos dois, cria um novo usuário.
        user = self.get_user_by_google_id(db, google_id=google_id)
        if user:
            logger.info(f"User found by google_id: {google_id}. Updating details if changed.")
            # Atualizar nome/foto se mudaram no Google ou se não definidos antes
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            if profile_picture_url and user.profile_picture_url != profile_picture_url:
                user.profile_picture_url = profile_picture_url
            # Considerar se o email pode mudar no Google e como tratar isso. Por ora, não atualizamos.
            db.commit()
            db.refresh(user)
            return user

        logger.info(f"User not found by google_id: {google_id}. Checking by email: {email}")
        user = self.get_user_by_email(db, email=email)
        if user:
            logger.info(f"User found by email: {email}. Associating google_id: {google_id} and updating details.")
            if not user.google_id: # Associar google_id se não estiver definido
                user.google_id = google_id
            # Atualizar nome/foto se não definidos ou se mudaram
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            if profile_picture_url and user.profile_picture_url != profile_picture_url:
                user.profile_picture_url = profile_picture_url
            db.commit()
            db.refresh(user)
            # Se o e-mail existe mas com um google_id diferente, é uma situação a ser tratada.
            # Por ora, se o email é o mesmo, é o mesmo usuário. Atualizamos google_id se estiver vazio.
            return user

        logger.info(f"No existing user found. Creating new user with google_id: {google_id} and email: {email}")
        return await self.create_user_oauth(
            db,
            email=email,
            google_id=google_id,
            full_name=full_name,
            profile_picture_url=profile_picture_url
        )

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

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def update_user_by_admin(self, db: Session, user_to_update: User, data_in: "UserUpdateByAdmin") -> User: # type: ignore
        update_data = data_in.model_dump(exclude_unset=True) # Pydantic V2
        # update_data = data_in.dict(exclude_unset=True) # Pydantic V1

        for field, value in update_data.items():
            setattr(user_to_update, field, value)

        db.add(user_to_update)
        db.commit()
        db.refresh(user_to_update)
        return user_to_update

    def add_permission(self, db: Session, user: User, permission: str) -> User:
        if permission not in user.permissions:
            user.permissions.append(permission)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def remove_permission(self, db: Session, user: User, permission: str) -> User:
        if permission in user.permissions:
            user.permissions.remove(permission)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

user_service = UserService()
