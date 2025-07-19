import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/auth_service/.env.test")

from app.services.user_service import UserService
from app.models.user_model import User, UserRole

# Instância do serviço a ser testado
user_service_instance = UserService()

@pytest.fixture
def mock_db_session():
    """Fixture para criar um mock da sessão do banco de dados SQLAlchemy."""
    session = MagicMock()
    # Configurar o mock para query, filter, first, add, commit, refresh
    # de forma que possam ser encadeados e retornem o que for necessário para os testes.
    session.query.return_value.filter.return_value.first.return_value = None # Default: usuário não encontrado
    return session

def test_get_or_create_user_oauth_new_user(mock_db_session):
    """Testa a criação de um novo usuário via OAuth."""
    mock_db_session.query(User).filter().first.return_value = None # Garante que nenhum usuário seja encontrado

    email = "newuser@example.com"
    google_id = "new_google_id_123"
    full_name = "New User"
    profile_picture_url = "http://example.com/newpic.jpg"

    created_user = user_service_instance.get_or_create_user_oauth(
        db=mock_db_session,
        email=email,
        google_id=google_id,
        full_name=full_name,
        profile_picture_url=profile_picture_url
    )

    # Verificar se db.add e db.commit foram chamados (indicando criação)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once() # create_user_oauth faz commit
    mock_db_session.refresh.assert_called_once_with(mock_db_session.add.call_args[0][0]) # Verifica se refresh foi chamado com o objeto de usuário

    # O objeto retornado deve ser o que foi passado para db.add
    user_passed_to_add = mock_db_session.add.call_args[0][0]
    assert created_user is user_passed_to_add
    assert created_user.email == email
    assert created_user.google_id == google_id
    assert created_user.full_name == full_name
    assert created_user.profile_picture_url == profile_picture_url
    assert created_user.is_active is True
    assert created_user.role == UserRole.ANALYST  # Verificar contra o Enum


def test_get_or_create_user_oauth_existing_user_by_google_id(mock_db_session):
    """Testa encontrar um usuário existente pelo google_id e atualizar seus dados."""
    existing_email = "existing@example.com"
    existing_google_id = "existing_google_id_456"
    original_full_name = "Old Name"
    new_full_name = "Updated Name"
    new_profile_picture_url = "http://example.com/updatedpic.jpg"

    mock_user = User(
        id=1,
        email=existing_email,
        google_id=existing_google_id,
        full_name=original_full_name,
        profile_picture_url=None # Sem foto de perfil original
    )
    # Configurar o mock para retornar este usuário quando consultado por google_id
    # e nenhum usuário quando consultado por e-mail (para simular a primeira checagem por google_id)
    mock_db_session.query(User).filter().first.side_effect = lambda *args, **kwargs: mock_user

    updated_user = user_service_instance.get_or_create_user_oauth(
        db=mock_db_session,
        email=existing_email, # Email pode ser o mesmo ou diferente, mas google_id deve encontrar
        google_id=existing_google_id,
        full_name=new_full_name,
        profile_picture_url=new_profile_picture_url
    )

    # Verificar se db.commit foi chamado (indicando atualização)
    # Na lógica atual, o commit é chamado mesmo se nada mudar, para user.google_id
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_user)

    assert updated_user.id == mock_user.id
    assert updated_user.email == existing_email
    assert updated_user.google_id == existing_google_id
    assert updated_user.full_name == new_full_name
    assert updated_user.profile_picture_url == new_profile_picture_url
    # db.add não deve ser chamado se o usuário foi encontrado
    mock_db_session.add.assert_not_called()


def test_get_or_create_user_oauth_existing_user_by_email_associate_google_id(mock_db_session):
    """Testa encontrar um usuário por e-mail, associar google_id e atualizar dados."""
    existing_email = "userbyemail@example.com"
    new_google_id = "new_google_id_for_email_user_789"
    original_full_name = "Email User Original Name"
    new_full_name = "Email User Updated Name"

    mock_user_by_email = User(
        id=2,
        email=existing_email,
        google_id=None, # Google ID não associado inicialmente
        full_name=original_full_name
    )

    # Simular: 1. Nenhum usuário por google_id. 2. Usuário encontrado por e-mail.
    def side_effect_filter_first(*args, **kwargs):
        # Esta é uma forma simplificada de simular o comportamento.
        # Uma abordagem mais robusta usaria múltiplos mocks ou checaria os `filter` args.
        # O primeiro `first()` (para google_id) retorna None.
        if mock_db_session.query(User).filter().first.call_count == 1:
            return None
        # O segundo `first()` (para email) retorna o mock_user_by_email.
        return mock_user_by_email

    mock_db_session.query(User).filter().first.side_effect = side_effect_filter_first

    updated_user = user_service_instance.get_or_create_user_oauth(
        db=mock_db_session,
        email=existing_email,
        google_id=new_google_id,
        full_name=new_full_name,
        profile_picture_url=None # Não estamos testando a atualização da foto aqui
    )

    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_user_by_email)

    assert updated_user.id == mock_user_by_email.id
    assert updated_user.email == existing_email
    assert updated_user.google_id == new_google_id # Google ID deve ser associado
    assert updated_user.full_name == new_full_name
    mock_db_session.add.assert_not_called() # Não cria novo, atualiza existente


def test_get_or_create_user_oauth_existing_user_by_google_id_no_changes(mock_db_session):
    """Testa encontrar um usuário existente pelo google_id sem alterações nos dados."""
    existing_email = "stableuser@example.com"
    existing_google_id = "stable_google_id_101"
    original_full_name = "Stable User"
    original_profile_picture_url = "http://example.com/stablepic.jpg"

    mock_user = User(
        id=3,
        email=existing_email,
        google_id=existing_google_id,
        full_name=original_full_name,
        profile_picture_url=original_profile_picture_url
    )
    mock_db_session.query(User).filter().first.return_value = mock_user

    updated_user = user_service_instance.get_or_create_user_oauth(
        db=mock_db_session,
        email=existing_email,
        google_id=existing_google_id,
        full_name=original_full_name, # Mesmo nome
        profile_picture_url=original_profile_picture_url # Mesma foto
    )

    # Mesmo que não haja mudanças, o código atual faz commit e refresh.
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_user)

    assert updated_user.full_name == original_full_name
    assert updated_user.profile_picture_url == original_profile_picture_url
    mock_db_session.add.assert_not_called()

def test_get_or_create_user_oauth_conflict_different_google_id(mock_db_session):
    """
    Testa o caso de conflito onde um usuário é encontrado por e-mail,
    mas já possui um google_id diferente do que foi fornecido.
    """
    existing_email = "conflict@example.com"
    existing_google_id = "google_id_already_set"
    new_google_id_from_login = "new_google_id_from_login_flow"

    mock_user_with_google_id = User(
        id=4,
        email=existing_email,
        google_id=existing_google_id
    )

    # Simular: 1. Nenhum usuário por new_google_id. 2. Usuário encontrado por e-mail.
    def side_effect_filter_first(*args, **kwargs):
        if mock_db_session.query(User).filter().first.call_count == 1:
            return None
        return mock_user_with_google_id

    mock_db_session.query(User).filter().first.side_effect = side_effect_filter_first

    # O serviço deve retornar o usuário existente sem alterar o google_id
    # ou, idealmente, logar um aviso de segurança.
    # A lógica atual não faz a verificação de conflito, apenas não atualiza.
    # Vamos testar o comportamento atual.
    result_user = user_service_instance.get_or_create_user_oauth(
        db=mock_db_session,
        email=existing_email,
        google_id=new_google_id_from_login,
        full_name="Any Name",
        profile_picture_url=None
    )

    # Verificar que o google_id original não foi sobrescrito
    assert result_user.google_id == existing_google_id
    assert result_user.google_id != new_google_id_from_login

    # O commit ainda será chamado por causa da atualização do nome/foto
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(mock_user_with_google_id)
