from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import FormatORM


class FormatRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        return self.session.query(FormatORM).all()

    def get_by_name(self, name):
        return self.session.query(FormatORM).filter(
            FormatORM.format_name == name
        ).first()

    def upsert(self, format_data):
        fmt = self.session.query(FormatORM).filter(
            FormatORM.format_name == format_data["format_name"]
        ).first()
        if fmt is None:
            fmt = FormatORM(**format_data)
            self.session.add(fmt)
        else:
            for key, value in format_data.items():
                setattr(fmt, key, value)
        self.session.flush()
        return fmt
