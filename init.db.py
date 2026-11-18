from app import app, db, User

with app.app_context():

    db.create_all()

    admin = User.query.filter_by(role="admin").first()
    if admin is None:
        new_admin = User(
            email="a@g.com",
            password="a123",
            role="admin",
            is_active=True
        )
        db.session.add(new_admin)
        db.session.commit()

        print("Admin created successfully.")
    else:
        print("Admin already exists.")