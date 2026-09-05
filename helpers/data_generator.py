from faker import Faker


fake = Faker('ru_RU')

def generate_user():
    return {
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'email': f"auto_{fake.uuid4()[:8]}@example.com",
        'phone': fake.phone_number(),
        'password': fake.password(length=12)
    }

def generate_news():
    return {
        'title': fake.sentence(nb_words=6).rstrip("."),
        'subtitle': fake.sentence(nb_words=4).rstrip("."),
        'text': fake.paragraph(nb_sentences=8),
        'tags':  ", ".join(fake.words(nb=4, unique=True))
    }

def generate_comment():
    return {'text': fake.sentence(nb_words=10)}

def generate_word():
    return fake.word()

def generate_email():
    return f"test_{fake.uuid4()[:8]}@example.com"