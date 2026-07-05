from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import CollectionORM


class CollectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        return self.session.query(CollectionORM).all()

    def get_owned(self, card_id):
        item = self.session.query(CollectionORM).filter(
            CollectionORM.card_id == card_id
        ).first()
        return item.owned if item else 0

    def set_owned(self, card_id, owned):
        item = self.session.query(CollectionORM).filter(
            CollectionORM.card_id == card_id
        ).first()
        if item is None:
            item = CollectionORM(card_id=card_id, owned=owned)
            self.session.add(item)
        else:
            item.owned = owned
        self.session.flush()
        return item

    def import_collection(self, items):
        count = 0
        for card_id, owned in items.items():
            self.set_owned(card_id, owned)
            count += 1
        self.session.flush()
        return count

    def delete_where_card_id_not_in(self, keep_ids):
        """Remove collection rows whose card_id is not in ``keep_ids``.

        Used to implement full-replace semantics on CSV import: every card not
        present in the imported file is dropped from the collection.
        """
        keep = {str(c) for c in keep_ids}
        deleted = (
            self.session.query(CollectionORM)
            .filter(~CollectionORM.card_id.in_(keep))
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return deleted

    def export_collection(self):
        items = self.session.query(CollectionORM).all()
        return {item.card_id: item.owned for item in items}
