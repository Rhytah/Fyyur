from datetime import datetime


from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venues', lazy=True)
    genres = db.relationship('Genre', secondary='venue_genre', viewonly=True)
    website = db.Column(db.String())
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.Text, nullable=True)
    deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Venue self.name {self.name}>'
    
    def add_genres(self, items):
        return [
            VenueGenre(venue_id=self.id, genre_id=genre)
            for genre in items
        ]

    def get_genres(self):
        return [genre.name for genre in self.genres]

    def update_genres(self, genres):
        #  first get the genres already present in database
        present_genres = VenueGenre.get_genres_ids(venue_id=self.id)

        # generate a differnecial list that picks new genres and adds them to the database
        new_genres = list(set(genres) - set(present_genres))
        if new_genres:
            genres_objs = self.add_genres(new_genres)
            db.session.add_all(genres_objs)

    def get_enum(self):
        return [
            (venue.id, venue.name)
            for venue in self.query.with_entities(self.id, self.name).all()
        ]

    def get_by_id(self, id):
        return self.query.filter_by(id=id).first_or_404()

    @classmethod
    def get_by_id_full(cls, id):
        details = {}
        venue = cls.get_by_id(id)
        past_shows = Show.get_past_by_venue(id)
        upcoming_shows = Show.get_upcoming_by_venue(id)
        details.update(venue)
        details.update({'upcoming_shows': upcoming_shows})
        details.update({'upcoming_shows_count': len(upcoming_shows)})
        details.update({'past_shows': past_shows})
        details.update({'past_shows_count': len(past_shows)})

        return details

    @classmethod
    def name_search(cls, venue_name):
        venues = cls.query.filter(
            cls.name.ilike(f'%{venue_name}%')
        ).all()
        return [
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": Show.count_upcoming_by_venue_id(venue.id)
            }
            for venue in venues
        ]

    def exists(self, name):
        return self.query.filter(db.func.lower(self.name) == db.func.lower(name)).count()

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id).serialize

    @classmethod
    def get_by_city_state(cls, state, city):
        state_venues = cls.query.filter_by(city=city, state=state).all()

        venues = [
            {
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": Show.count_upcoming_by_venue_id(venue.id)
            }
            for venue in state_venues
        ]
        return venues

    @classmethod
    def get_all(cls):
        venues = cls.query.with_entities(cls.city, cls.state).group_by(cls.state, cls.city).all()
        results = [
            {
                'city': venue.city,
                'state': venue.state,
                'venues': cls.get_by_city_state(state=venue.state, city=venue.city)
            }
            for venue in venues
        ]

        return results

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'genres': self.get_genres(),
            'city': self.city,
            'state': self.state,
            'address': self.address,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_talent': self.seeking_talent,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link
        }



class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    shows = db.relationship('Show', backref='Artist', lazy=True)
    genres = db.relationship('Genre', secondary='artist_genre', viewonly=True)
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.Text)
    website = db.Column(db.String(200))


    def __repr__(self):
        return f'<Artist self.id {self.name}>'


    def add_genres(self, items):
        return [
            ArtistGenre(artist_id=self.id, genre_id=genre)
            for genre in items
        ]

    def get_genres(self):
        return [genre.name for genre in self.genres]

    def update_genres(self, genres):
        venue_genres_in_db = ArtistGenre.get_genres_ids(artist_id=self.id)

        # generate a list of new genres not in db
        genres_to_insert = list(set(genres) - set(venue_genres_in_db))
        if genres_to_insert:
            genres_objs = self.add_genres(genres_to_insert)
            db.session.add_all(genres_objs)

    @classmethod
    def get_enum(cls):
        return [
            (artist.id, artist.name)
            for artist in cls.query.with_entities(cls.id, cls.name).all()
        ]

    @classmethod
    def get_by_id(cls, id):
        return cls.query.get_or_404(id)

    @classmethod
    def get_by_id_full(cls, id):
        details = {}
        artist = cls.get_by_id(id)
        past_shows = Show.get_past_by_venue(id)
        upcoming_shows = Show.get_upcoming_by_artist(id)
        details.update(artist.serialize)
        details.update({'upcoming_shows': upcoming_shows})
        details.update({'upcoming_shows_count': len(upcoming_shows)})
        details.update({'past_shows': past_shows})
        details.update({'past_shows_count': len(past_shows)})

        return details

    @classmethod
    def search_artist_name(cls, name):
        artists = cls.query.filter(cls.name.ilike(f'%{name}%')).outerjoin(Show, cls.id == Show.artist_id).all()
        return [{
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": artist.num_upcoming_shows
        } for artist in artists]

    @classmethod
    def exists(cls, name):
        return cls.query.filter(db.func.lower(cls.name) == db.func.lower(name)).count()

    @property
    def num_upcoming_shows(self):
        return self.query.join(Show).filter_by(artist_id=self.id).filter(
            Show.start_time > datetime.now()).count()

    @property
    def num_past_shows(self):
        return self.query.join(Show).filter_by(artist_id=self.id).filter(
            Show.start_time < datetime.now()).count()

    @property
    def past_shows(self):
        return Show.get_past_by_artist(self.id)

    @property
    def upcoming_shows(self):
        return Show.get_upcoming_by_artist(self.id)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'genres': self.get_genres(),
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_venue': self.seeking_venue,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link
        }

    def __repr__(self):
        return f'<Artist name: {self.name}>'
    
class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    artist_id= db.Column(db.Integer, db.ForeignKey('Artist.id'))
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'))
    start_time = db.Column(db.DateTime)
    artist = db.relationship('Artist', viewonly=True)
    venue = db.relationship('Venue', viewonly=True)

    def __repr__(self):
        return f'<Show id: {self.id} artist_id:{self.artist_id} venue_id: {self.venue_id}'
    @classmethod
    def count_upcoming_by_venue_id(cls, venue_id):
        return cls.query.filter_by(venue_id=venue_id).filter(cls.start_time > datetime.now()).count()

    @classmethod
    def count_past_by_venue_id(cls, venue_id):
        return cls.query.filter_by(venue_id=venue_id).filter(cls.start_time < datetime.now()).count()

    @classmethod
    def get_past_by_venue(cls, venue_id):
        shows = cls.query.filter_by(venue_id=venue_id).filter(cls.start_time < datetime.now()).all()
        return [show.show_details for show in shows]

    @classmethod
    def get_past_by_artist(cls, artist_id):
        shows = cls.query.filter_by(artist_id=artist_id).filter(cls.start_time < datetime.now()).all()
        return [show.show_details for show in shows]

    @classmethod
    def get_upcoming_by_venue(cls, venue_id):
        shows = cls.query.filter_by(venue_id=venue_id).filter(Show.start_time > datetime.now()).all()
        return [show.show_details for show in shows]

    @classmethod
    def get_upcoming_by_artist(cls, artist_id):
        shows = cls.query.filter_by(artist_id=artist_id).filter(Show.start_time > datetime.now()).all()
        return [show.show_details for show in shows]

    @classmethod
    def get_all(cls):
        return [show.show_details for show in cls.query.order_by(cls.venue_id.desc()).all()]

    @property
    def show_details(self):
        return {
            'id': self.id,
            'venue_id': self.venue_id,
            'venue_name': self.venue.name,
            "artist_id": self.artist_id,
            "artist_name": self.artist.name,
            "artist_image_link": self.artist.image_link,
            'start_time': self.start_time.strftime("%m/%d/%Y, %H:%M")
        }

class Genre(db.Model):
    __tablename__ = 'genres'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    artists = db.relationship('Artist', secondary='artist_genre', viewonly=True)
    venues = db.relationship('Venue', secondary='venue_genre', viewonly=True)

    @classmethod
    def get_enum(cls):
        return [(genre.id, genre.name) for genre in cls.query.all()]

    def details(self):
        return {
            'id': self.id,
            'name': self.name
        }

    def __repr__(self):
        return f'<Genre name = {self.name}/>'


class ArtistGenre(db.Model):
    __tablename__ = 'artist_genre'

    genre_id = db.Column(db.Integer, db.ForeignKey('genres.id'), primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), primary_key=True)

    genre = db.relationship('Genre', backref=db.backref('artist_genre', cascade='all, delete-orphan'))
    artist = db.relationship('Artist', backref=db.backref('artist_genre', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint(genre_id, artist_id),)

    @classmethod
    def delete_old(cls, artist_id, genres):
        venues_to_delete = db.session.query(cls).filter_by(artist_id=artist_id).filter(cls.genre_id.notin_(genres))
        venues_to_delete.delete(synchronize_session=False)

    @classmethod
    def get_genres_ids(cls, artist_id):
        results = cls.query.filter_by(artist_id=artist_id).all()
        return [str(result.genre_id) for result in results]

    def __repr__(self):
        return f'<ArtistGenre artist {self.artist_id} genre {self.artist_id}>'


class VenueGenre(db.Model):
    __tablename__ = 'venue_genre'

    genre_id = db.Column(db.Integer, db.ForeignKey('genres.id'), primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), primary_key=True)

    genre = db.relationship('Genre', backref=db.backref('venue_genre', cascade='all, delete-orphan'))
    venue = db.relationship('Venue', backref=db.backref('venue_genre', cascade='all, delete-orphan'))

    __table_args__ = (db.UniqueConstraint(genre_id, venue_id),)

    @classmethod
    def delete_old(cls, venue_id, genres):
        venues_to_delete = db.session.query(cls).filter_by(venue_id=venue_id).filter(cls.genre_id.notin_(genres))
        venues_to_delete.delete(synchronize_session=False)

    @classmethod
    def get_genres_ids(cls, venue_id):
        results = cls.query.filter_by(venue_id=venue_id).all()
        return [str(result.genre_id) for result in results]

    def __repr__(self):
        return f'<VenreGenre venue {self.venue_id} genre {self.genre_id}>'