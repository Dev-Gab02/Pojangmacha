from sqlalchemy import Column, Integer, String, Float, Text
from core.db import Base

class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_path = Column(String, nullable=True)

    def __repr__(self):
        return f"<FoodItem {self.name} ₱{self.price}>"
