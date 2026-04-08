from app.user.domain.domain_service import UserDomainService
from app.user.domain.repository.user import UserRepository


class SQLAlchemyUserDomainService(UserDomainService):
    def __init__(self, *, user_repository: UserRepository):
        super().__init__(user_repository=user_repository)
