import unittest
from app import create_app, db
from app.models import User, Review, Tag, Whisky, Distillery
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='bobby')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128),
                         ('https://www.gravatar.com/avatar/d4c74594d841139328695756648b6bd6?d=identicon&s=128'))

    def test_models(self):
        user = User(username='john', email='john@example.com')
        dist1 = Distillery(name='TestDistillery')
        whisky1 = Whisky(name='TestWhisky', distillery=dist1)
        review1 = Review(nose='Review 1', author=user, whisky=whisky1)
        review2 = Review(nose='Review 2', author=user)
        tag1 = Tag(name='sweet')
        tag2 = Tag(name='sour')

        db.session.add(user)
        db.session.add(dist1)
        db.session.add(whisky1)
        db.session.add(review1)
        db.session.add(review2)
        db.session.add(tag1)
        db.session.add(tag2)
        db.session.commit()

        # Test Whisky and Distillery logic
        self.assertEqual(review1.whisky_id, whisky1.id)
        self.assertEqual(whisky1.number_reviews(),  1)
        self.assertEqual(whisky1.distillery_id, dist1.id)

        # Test adding tags
        self.assertEqual(review1.tags.all(), [])
        review1.add_tag(tag1)
        review2.add_tag(tag2)
        db.session.commit()
        self.assertTrue(review1.is_tagged(tag1))
        self.assertFalse(review1.is_tagged(tag2))
        self.assertFalse(review2.is_tagged(tag1))
        self.assertTrue(review2.is_tagged(tag2))
        self.assertEqual(review1.tags.count(), 1)
        self.assertEqual(review1.tags.first().name, 'sweet')

        # Test removing tags
        review1.remove_tag(tag1)
        db.session.commit()
        self.assertFalse(review1.is_tagged(tag1))
        self.assertEqual(review1.tags.count(), 0)
        self.assertEqual(review2.tags.count(), 1)

        # Test adding whiskies to user
        self.assertEqual(user.get_whiskies_listed(), [])
        user.add_whisky(whisky1)
        self.assertTrue(user.has_whisky(whisky1))
        user.remove_whisky(whisky1)
        self.assertFalse(user.has_whisky(whisky1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
