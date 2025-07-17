import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.linked_account_model import Base, LinkedAccount, CloudProviderEnum
from app.crud.crud_linked_account import linked_account_crud
from app.schemas.linked_account_schema import LinkedAccountCreate

# Usar um banco de dados em memória para os testes de unidade do CRUD
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar as tabelas no início da sessão de testes
Base.metadata.create_all(bind=engine)

@pytest.fixture()
def db_session():
    """Fixture para criar uma sessão de banco de dados para cada teste."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(autouse=True)
def cleanup_db(db_session):
    """Limpa a tabela após cada teste."""
    yield
    db_session.query(LinkedAccount).delete()
    db_session.commit()

def test_create_linked_account(db_session):
    account_in = LinkedAccountCreate(
        name="Test AWS Account",
        provider=CloudProviderEnum.AWS,
        account_id="123456789012",
        credentials={"key": "value"} # Credentials não são salvas no DB
    )
    db_account = linked_account_crud.create(db=db_session, obj_in=account_in)

    assert db_account.id is not None
    assert db_account.name == "Test AWS Account"
    assert db_account.provider == CloudProviderEnum.AWS
    assert db_account.account_id == "123456789012"

def test_get_linked_account(db_session):
    account_in = LinkedAccountCreate(name="Test Account", provider=CloudProviderEnum.GCP, account_id="gcp-project-1", credentials={})
    created_account = linked_account_crud.create(db=db_session, obj_in=account_in)

    fetched_account = linked_account_crud.get(db=db_session, id=created_account.id)

    assert fetched_account is not None
    assert fetched_account.id == created_account.id
    assert fetched_account.name == "Test Account"

def test_get_multi_linked_accounts(db_session):
    linked_account_crud.create(db=db_session, obj_in=LinkedAccountCreate(name="Acc 1", provider=CloudProviderEnum.AWS, account_id="1", credentials={}))
    linked_account_crud.create(db=db_session, obj_in=LinkedAccountCreate(name="Acc 2", provider=CloudProviderEnum.GCP, account_id="2", credentials={}))

    accounts = linked_account_crud.get_multi(db=db_session)
    assert len(accounts) == 2

def test_remove_linked_account(db_session):
    account_in = LinkedAccountCreate(name="To Be Deleted", provider=CloudProviderEnum.AZURE, account_id="azure-sub-1", credentials={})
    created_account = linked_account_crud.create(db=db_session, obj_in=account_in)

    removed_account = linked_account_crud.remove(db=db_session, id=created_account.id)

    assert removed_account is not None
    assert removed_account.id == created_account.id

    assert linked_account_crud.get(db=db_session, id=created_account.id) is None
