import uvicorn

from pydantic import BaseModel
from fastapi import FastAPI, status, HTTPException
from typing import List

from pydantic.class_validators import Optional
from sqlalchemy import String, Integer, Column, Text, ForeignKey, Float
from sqlalchemy.orm import relationship

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

engine = create_engine("postgresql://postgres:1522613aA@localhost:5432/menudb", echo=True)

Base = declarative_base()

SessionLocal = sessionmaker(bind=engine)

app = FastAPI()
session = SessionLocal()


class Menu(Base):
    __tablename__ = 'menu'
    id: int = Column(Integer, primary_key=True, nullable=False)
    title: str = Column(String, unique=True, nullable=False)
    description: str = Column(String, nullable=False)
    submenu: list = relationship("Submenu", backref='menu', cascade="all, delete-orphan")
    dishes_count: Optional[int] = 0
    submenus_count: Optional[int] = 0


class Submenu(Base):
    __tablename__ = 'submenu'
    id: int = Column(Integer, primary_key=True, nullable=False)
    title: str = Column(String, unique=True, nullable=False)
    description: str = Column(String, nullable=False)
    dishes: list = relationship("Dish", backref="submenu", cascade="all, delete-orphan")
    menu_id: int = Column(Integer, ForeignKey("menu.id"), nullable=False)
    dishes_count: Optional[int] = 0

    def count(self):
        return len(self.dishes)


class Dish(Base):
    __tablename__ = 'dish'
    id: int = Column(Integer, primary_key=True, nullable=False)
    title: str = Column(String(255), unique=True, nullable=False)
    price: float = Column(Float)
    description: str = Column(Text, nullable=False)
    submenu_id: int = Column(Integer, ForeignKey("submenu.id"), nullable=False)


Base.metadata.create_all(engine)


class BaseSchema(BaseModel):
    id: int | None

    class Config:
        orm_mode = True


class MenuSchema(BaseSchema):  # Serializers
    title: str
    description: str
    dishes_count: int | None
    submenus_count: int | None

    class Config:
        orm_mode = True


class SubmenuSchema(BaseSchema):  # Serializers
    title: str
    description: str
    dishes_count: int | None

    class Config:
        orm_mode = True


class DishSchema(BaseSchema):  # Serializers
    title: str
    description: str
    price: float

    class Config:
        orm_mode = True


@app.get('/api/v1/menus', response_model=List[MenuSchema], status_code=status.HTTP_200_OK)
async def menu_get_all():
    return session.query(Menu).all()


@app.get('/api/v1/menus/{target_menu_id}', response_model=MenuSchema, status_code=status.HTTP_200_OK)
async def menu_get(target_menu_id: int):
    menu = session.query(Menu).filter(Menu.id == target_menu_id).first()

    if menu is None:
        raise HTTPException(404, detail="menu not found")

    menu.id = target_menu_id

    if menu.submenu:
        menu.submenus_count = len(menu.submenu)
        if menu.submenu[0].dishes:
            menu.dishes_count = len(menu.submenu[0].dishes)  # fixme: опасная ситуация, а если подменюшек будет больше?

    return menu


@app.post('/api/v1/menus', response_model=MenuSchema, status_code=status.HTTP_201_CREATED)
async def menu_create(menu: MenuSchema):
    new_menu = Menu(
        id=menu.id,
        title=menu.title,
        description=menu.description
    )
    session.add(new_menu)
    session.commit()
    session.refresh(new_menu)

    return new_menu


@app.patch('/api/v1/menus/{target_menu_id}', response_model=MenuSchema, status_code=status.HTTP_200_OK)
async def menu_update(target_menu_id: int, menu: MenuSchema):
    menu_to_update = session.query(Menu).filter(Menu.id == target_menu_id).first()
    menu_to_update.title = menu.title
    menu_to_update.description = menu.description
    session.commit()
    return menu_to_update


@app.delete('/api/v1/menus/{target_menu_id}')
async def menu_delete(target_menu_id: int):
    menu_to_delete = session.query(Menu).filter(Menu.id == target_menu_id).first()
    session.delete(menu_to_delete)

    session.commit()

    return status.HTTP_200_OK


@app.get('/api/v1/menus/{target_menu_id}/submenus', response_model=List[SubmenuSchema], status_code=status.HTTP_200_OK)
def submenu_get_all(target_menu_id: int):
    return session.query(Submenu).filter(Submenu.menu_id == target_menu_id).all()


@app.get('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}', response_model=SubmenuSchema,
         status_code=status.HTTP_200_OK)
def submenu_get(target_menu_id: int, target_submenu_id: int):
    submenu = session.query(Submenu) \
        .filter(Submenu.menu_id == target_menu_id
                and Submenu.id == target_submenu_id)\
        .first()

    if submenu is None:
        raise HTTPException(404, "submenu not found")

    submenu.dishes_count = submenu.count()
    return submenu


@app.post('/api/v1/menus/{target_menu_id}/submenus', response_model=SubmenuSchema, status_code=status.HTTP_201_CREATED)
def submenu_create(target_menu_id: int, submenu: SubmenuSchema):
    nwe_submenu = Submenu(
        menu_id=target_menu_id,
        title=submenu.title,
        description=submenu.description
    )

    session.add(nwe_submenu)
    session.commit()

    return nwe_submenu


@app.patch('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}', response_model=SubmenuSchema,
           status_code=status.HTTP_200_OK)
def submenu_update(target_menu_id: int, target_submenu_id: int, submenu: SubmenuSchema):
    submenu_to_update = session.query(Submenu) \
        .filter(Submenu.menu_id == target_menu_id
                and Submenu.id == target_submenu_id)\
        .first()
    submenu_to_update.title = submenu.title
    submenu_to_update.description = submenu.description

    session.commit()

    return submenu_to_update


@app.delete('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}', status_code=status.HTTP_200_OK)
def submenu_delete(target_menu_id: int, target_submenu_id: int):
    submenu = session.query(Submenu) \
        .filter(Submenu.menu_id == target_menu_id) \
        .filter(Submenu.id == target_submenu_id) \
        .first()
    session.delete(submenu)
    session.commit()


@app.get('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes', response_model=List[DishSchema],
         status_code=status.HTTP_200_OK)
def dish_all(target_menu_id: int, target_submenu_id: int):
    submenu = session.query(Submenu) \
        .filter(Submenu.id == target_submenu_id
                and Submenu.menu_id == target_menu_id) \
        .first()

    if submenu is None:
        return []

    dish_list: List[Dish] = submenu.dishes
    if not dish_list:
        return []

    return dish_list


@app.get('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes/{target_dish_id}',
         response_model=DishSchema, status_code=status.HTTP_200_OK)
def dish_get(target_menu_id: int, target_submenu_id: int, target_dish_id: int):
    dish: Dish = session.query(Dish) \
        .join(Submenu) \
        .filter(Submenu.menu_id == target_menu_id
                and Submenu.id == target_submenu_id
                and Dish.submenu_id == Submenu.id
                and Dish.id == target_dish_id) \
        .first()

    if dish is None:
        raise HTTPException(404, "dish not found")

    return dish


@app.post('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes', response_model=DishSchema,
          status_code=status.HTTP_201_CREATED)
def dish_create(target_menu_id: int, target_submenu_id: int, dish: DishSchema):
    submenu = session.query(Submenu) \
        .filter(Submenu.id == target_submenu_id
                and Submenu.menu_id == target_menu_id) \
        .first()

    if submenu is None:
        raise HTTPException(404, "submenu with target_menu_id="
                            + str(target_menu_id)
                            + " and target_submenu_id="
                            + str(target_submenu_id) + " not found")

    new_dish = Dish(
        title=dish.title,
        price=dish.price,
        description=dish.description
    )
    submenu.dishes.append(new_dish)
    session.add(new_dish)
    session.commit()

    return new_dish


@app.patch('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes/{target_dish_id}',
           response_model=DishSchema, status_code=status.HTTP_200_OK)
def dish_update(target_menu_id: int, target_submenu_id: int, target_dish_id: int, dish: DishSchema):
    dish_to_update = session.query(Dish) \
        .join(Submenu) \
        .filter(Submenu.id == target_submenu_id
                and Submenu.menu_id == target_menu_id
                and Dish.id == target_dish_id
                and Dish.submenu_id == Submenu.id) \
        .first()

    if dish is None:
        raise HTTPException(404, "dish with target_menu_id=" + str(target_menu_id) + " and target_submenu_id=" + str(
            target_submenu_id) + " not found")

    dish_to_update.title = dish.title
    dish_to_update.price = dish.price
    dish_to_update.description = dish.description

    session.commit()

    return dish_to_update


@app.delete('/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes/{target_dish_id}',
            status_code=status.HTTP_200_OK)
def dish_delete(target_menu_id: int, target_submenu_id: int, target_dish_id: int):
    dish_to_delete = session.query(Dish) \
        .join(Submenu) \
        .filter(Submenu.id == target_submenu_id
                and Submenu.menu_id == target_menu_id
                and Dish.id == target_dish_id
                and Dish.submenu_id == Submenu.id) \
        .first()

    if dish_to_delete is None:
        raise HTTPException(404, "dish with target_dish_id=" + str(target_dish_id) + " not found!")

    session.delete(dish_to_delete)
    session.commit()


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=80)
