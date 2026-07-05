from sqlalchemy.orm import Session


class MatchRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        raise NotImplementedError

    def get_by_id(self):
        raise NotImplementedError

    def create(self):
        raise NotImplementedError
