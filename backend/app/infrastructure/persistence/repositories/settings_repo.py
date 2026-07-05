from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import SettingsORM


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, key, default=None):
        setting = self.session.query(SettingsORM).filter(SettingsORM.key == key).first()
        if setting is None:
            return default
        return setting.value

    def set(self, key, value):
        setting = self.session.query(SettingsORM).filter(SettingsORM.key == key).first()
        if setting is None:
            setting = SettingsORM(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        self.session.commit()

    def get_all(self):
        settings = self.session.query(SettingsORM).all()
        return {s.key: s.value for s in settings}
