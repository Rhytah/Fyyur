#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import sys
from datetime import datetime

from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate=Migrate(app,db)

# TODO: connect to a local postgresql database

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
        #  genres in db
        venue_genres_in_db = VenueGenre.get_genres_ids(venue_id=self.id)

        # generate a list of new genres not in db
        genres_to_insert = list(set(genres) - set(venue_genres_in_db))
        if genres_to_insert:
            genres_objs = self.add_genres(genres_to_insert)
            db.session.add_all(genres_objs)

    @classmethod
    def get_enum(cls):
        return [
            (venue.id, venue.name)
            for venue in cls.query.with_entities(cls.id, cls.name).all()
        ]

    @classmethod
    def get_by_id(cls, id):
        return cls.query.filter_by(id=id).first_or_404()

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
    def search_by_name(cls, venue_name):
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

    @classmethod
    def exists(cls, name):
        return cls.query.filter(db.func.lower(cls.name) == db.func.lower(name)).count()

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
    def get_artists_by_name(cls, name):
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

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime


#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  data = Venue.get_all()
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
 
    search_term = request.form.get('search_term')
    results = Venue.search_by_name(search_term)
    response = {
        'count': len(results),
        'data': results
    }

    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  data1={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    "past_shows": [{
      "artist_id": 4,
      "artist_name": "Guns N Petals",
      "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
      "start_time": "2019-05-21T21:30:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }
  data2={
    "id": 2,
    "name": "The Dueling Pianos Bar",
    "genres": ["Classical", "R&B", "Hip-Hop"],
    "address": "335 Delancey Street",
    "city": "New York",
    "state": "NY",
    "phone": "914-003-1132",
    "website": "https://www.theduelingpianos.com",
    "facebook_link": "https://www.facebook.com/theduelingpianos",
    "seeking_talent": False,
    "image_link": "https://images.unsplash.com/photo-1497032205916-ac775f0649ae?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=750&q=80",
    "past_shows": [],
    "upcoming_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0,
  }
  data3={
    "id": 3,
    "name": "Park Square Live Music & Coffee",
    "genres": ["Rock n Roll", "Jazz", "Classical", "Folk"],
    "address": "34 Whiskey Moore Ave",
    "city": "San Francisco",
    "state": "CA",
    "phone": "415-000-1234",
    "website": "https://www.parksquarelivemusicandcoffee.com",
    "facebook_link": "https://www.facebook.com/ParkSquareLiveMusicAndCoffee",
    "seeking_talent": False,
    "image_link": "https://images.unsplash.com/photo-1485686531765-ba63b07845a7?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=747&q=80",
    "past_shows": [{
      "artist_id": 5,
      "artist_name": "Matt Quevedo",
      "artist_image_link": "https://images.unsplash.com/photo-1495223153807-b916f75de8c5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=334&q=80",
      "start_time": "2019-06-15T23:00:00.000Z"
    }],
    "upcoming_shows": [{
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-01T20:00:00.000Z"
    }, {
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-08T20:00:00.000Z"
    }, {
      "artist_id": 6,
      "artist_name": "The Wild Sax Band",
      "artist_image_link": "https://images.unsplash.com/photo-1558369981-f9ca78462e61?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=794&q=80",
      "start_time": "2035-04-15T20:00:00.000Z"
    }],
    "past_shows_count": 1,
    "upcoming_shows_count": 1,
  }
 
  data = Venue.get_by_id_full(venue_id)
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  # flash('Venue ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  # return render_template('pages/home.html')

    try:
      name = request.form['name']
      city = request.form['city']
      state = request.form['state']
      address = request.form['address']
      phone = request.form['phone']
      image_link = request.form['image_link']
      facebook_link = request.form['facebook_link']
      venue = Venue(name = name,city=city,state=state,address=address,phone=phone, image_link=image_link, facebook_link=facebook_link)
      db.session.add(venue)
      db.session.commit()

      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
      db.session.rollback()
      flash('An error occurred. Venue could not be listed.')

    finally:
      db.session.close()
      return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database

  return render_template('pages/artists.html', artists=Artist.query.all())

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term = request.form.get('search_term')
  artists = Artist.get_artists_by_name(search_term)

  response = {
      "count": len(artists),
      "data": artists
  }
  return render_template('pages/search_artists.html', results=response,
                          search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  data = Artist.get_by_id_full(artist_id)
  return render_template('pages/show_artist.html', artist=data)
  
#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.get_by_id(artist_id).serialize

  # set current genres
  artist['genres'] = ArtistGenre.get_genres_ids(artist_id)

  form = ArtistForm(**artist)
  form.genres.choices = Genre.get_enum()

  return render_template('forms/edit_artist.html', form=form, artist=artist)
 
  # TODO: populate form with fields from artist with ID <artist_id>

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attribute
  form=ArtistForm()
  try:
      artist = Artist.query.get(artist_id)
      artist.name = request.form['name']
      artist.city = request.form['city']
      artist.state = request.form['state']
      artist.phone = request.form['phone']
      artist.image_link = request.form['image_link']
      artist.facebook_link = request.form['facebook_link']
      artist.website = request.form['website']
      artist.seeking_venue=request.form['seeking_venue']
      artist.seeking_description=request.form['seeking_description']
      updated_genres = request.form['genres']

      # Delete genres that are not in updated_genres
      ArtistGenre.delete_old(artist_id=artist_id, genres=updated_genres)
      # update venue genres
      artist.update_genres(updated_genres)
      db.session.commit()
  except:
      print(sys.exc_info())
      db.session.rollback()

  finally:
      db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.get_by_id(venue_id)
  form = VenueForm(**venue)
  # set current genres
  venue['genres'] = VenueGenre.get_genres_ids(venue_id)
  #  set genres list
  form.genres.choices = Genre.get_enum()

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  name = request.form['name']
  city = request.form['city']
  state = request.form['state']
  phone = request.form['phone']
  image_link = request.form['image_link']
  facebook_link = request.form['facebook_link']
  genres=request.form['genres']
  new_artist = Artist(name = name,city=city,state=state,phone=phone, image_link=image_link, facebook_link=facebook_link)
  db.session.add(new_artist)
  db.session.commit()
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
  flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  data = Show.get_all()
  return render_template('pages/shows.html', shows=data)
 

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
    try:
      artist_id = request.form['artist_id']
      venue_id = request.form['venue_id']
      start_time = request.form['start_time']
      show = Show(artist_id = artist_id,venue_id=venue_id,start_time=start_time)
      db.session.add(show)
      db.session.commit()
      
      # return render_template('pages/shows.html')
      flash('You have added a new show')

    except:
      db.session.rollback()
      flash('An error occurred. Show could not be listed.')
      print('failed')

    finally:
      db.session.close()
  
      return render_template('pages/home.html')
      print('the final statement in try catch')
  # on successful db insert, flash success
  # flash('Show was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  # return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
