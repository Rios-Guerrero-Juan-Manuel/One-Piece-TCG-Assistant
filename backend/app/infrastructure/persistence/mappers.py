from app.domain.models import Card
from app.infrastructure.persistence.models import CardORM


def orm_to_card(orm: CardORM) -> Card:
    return Card(
        card_id=orm.card_id,
        name=orm.name,
        cost=orm.cost,
        power=orm.power,
        counter=orm.counter,
        type=orm.type,
        color=orm.color or [],
        traits=orm.traits or [],
        attribute=orm.attribute,
        keywords=orm.keywords or [],
        roles=orm.roles or [],
        effect=orm.effect or "",
        life=orm.life,
        set_id=orm.set_id,
        set_name=orm.set_name,
        rarity=orm.rarity,
        image_url=orm.image_url,
        unlimited_copies=orm.unlimited_copies,
    )
