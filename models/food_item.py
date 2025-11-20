# models/food_item.py
from sqlalchemy import Column, Integer, String, Float
from core.db import Base

class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)  # Ramen, Buldak, Rice Bowl, Drinks
    price = Column(Float, nullable=False)
    image = Column(String, nullable=True)  # store path of image
