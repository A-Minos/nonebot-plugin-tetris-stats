from ...schemas import BaseUser


class User(BaseUser):
    ID: str | None = None
    name: str | None = None

    @property
    def unique_identifier(self) -> str:
        if self.ID is None:
            raise ValueError('不完整的User!')
        return self.ID
