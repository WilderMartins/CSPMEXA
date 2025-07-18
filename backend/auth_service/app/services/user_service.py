from sqlalchemy.orm import Session
from typing import Optional

from app.models.user_model import User, UserRole # Importar UserRole
from app.schemas.user_schema import UserCreate, UserUpdateByAdmin # UserUpdateByAdmin é usado no tipo hint
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
        full_name: Optional[str] = None,
        profile_picture_url: Optional[str] = None
    ) -> User:
        logger.info(f"Creating new OAuth user for email: {email}, google_id: {google_id}")
        # Aqui, não estamos definindo uma senha local, pois é um login OAuth
        # is_active, is_superuser e role terão seus defaults do modelo User
        db_user = User(
            email=email,
            google_id=google_id,
            full_name=full_name,
            profile_picture_url=profile_picture_url,
            is_active=True,
            is_superuser=False, # Manter is_superuser para compatibilidade ou usos futuros específicos
            role=UserRole.USER # Definir explicitamente o papel padrão na criação
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
        full_name: Optional[str] = None,
        profile_picture_url: Optional[str] = None
    ) -> User:
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
        return self.create_user_oauth(
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

    def set_user_role(self, db: Session, user: User, role: UserRole) -> User:
        """Define o papel de um usuário. O input 'role' deve ser um membro do Enum UserRole."""
        if not isinstance(role, UserRole):
            raise ValueError("O papel fornecido deve ser um membro do Enum UserRole.")
        user.role = role
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def set_initial_admin_user(self, db: Session) -> Optional[User]:
        """
        Define o primeiro usuário encontrado como SuperAdministrator,
        se nenhum SuperAdministrator existir. Útil para setup inicial.
        Retorna o usuário SuperAdministrator ou None se nenhum usuário foi modificado/encontrado.
        """
        # Verificar se já existe algum SuperAdministrator
        super_admin_user = db.query(User).filter(User.role == UserRole.SUPER_ADMINISTRATOR).first()
        if super_admin_user:
            logger.info(f"SuperAdministrator user already exists: {super_admin_user.email}")
            return super_admin_user

        # Alternativamente, verificar por Administrator também, se a lógica for essa
        admin_user = db.query(User).filter(User.role == UserRole.ADMINISTRATOR).first()
        if admin_user: # Se já houver um admin, talvez não criar um super automaticamente? Ou promover?
            logger.info(f"Administrator user exists: {admin_user.email}. Consider promoting or defining SuperAdmin manually if needed.")
            # Dependendo da lógica desejada, pode-se parar aqui ou continuar para criar um SuperAdmin
            # return admin_user # Se um Admin já for suficiente

        # Se não houver SuperAdmin, tornar o primeiro usuário (ordenado por ID) um SuperAdmin
        first_user = db.query(User).order_by(User.id).first()

        if first_user:
            logger.info(f"Setting user {first_user.email} (ID: {first_user.id}) as initial SuperAdministrator.")
            # Adicionalmente, pode-se definir is_superuser = True, embora redundante com o role.
            first_user.is_superuser = True
            return self.set_user_role(db, user=first_user, role=UserRole.SUPER_ADMINISTRATOR)
        else:
            logger.warning("No users found in the database to set as initial SuperAdministrator.")
            return None

user_service = UserService()
