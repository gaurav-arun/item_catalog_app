from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    category = Column(String(250), nullable=False)
    description = Column(String(1024), nullable=False)
    image = Column(String(1024), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    last_updated_on = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship(User)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'created by': {
                'id': self.user.id,
                'username': self.user.name
            }
        }


engine = create_engine('sqlite:///db/itemcatalog.db', connect_args={'check_same_thread': False})
Base.metadata.create_all(engine)
