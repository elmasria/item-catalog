from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from setup import *
import json


engine = create_engine('sqlite:///catalog.db')


Base.metadata.bind = engine
db_session = sessionmaker(bind=engine)()


if db_session.query(Category).first() == None:
    # load data from JSON file
    with open('data.json', 'rb') as file:
        data = json.load(file)

    # Loop through 'category-list' data, create 'Category' object for each
    # iteration and store in database
    for item in data['category-list']:
        category = Category(name=item['name'],
                            description=item['description'])
        db_session.add(category)

    # Loop through 'item-list' data, create 'Book' object for each iteration
    # and store in database
    for item in data['item-list']:
        new_item = Item(name=item['name'],
                        thumbnail_url=item['thumbnail_url'],
                        description=item['description'],
                        category_id=item['category_id'])
        db_session.add(new_item)

    # Commit imported data to database
    db_session.commit()

    # Display messgae to console to verify import in complete
    print "import complete"