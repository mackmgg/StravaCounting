from flask import Flask
import flask
from stravalib.client import Client
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
import datetime
import sys
import os
import secrets
from waitress import serve

serverURL = "https://strava.mack.im" # Needs to be updated on server

app = Flask(__name__)
app.secret_key = secrets.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///strava'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class GreensModel(db.Model):
	__tablename__ = 'greens'
	
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String())
	num = db.Column(db.Integer)
	lastupdate = db.Column(sqlalchemy.types.TIMESTAMP)

	def __init__(self, name, id, greens, lastupdate):
		self.name = name
		self.id = id
		self.num = greens
		self.lastupdate = lastupdate
	
	def __repr__(self):
		return f"<Green {self.name}>"

@app.route("/")
def main_page():
	sqlQuery = GreensModel.query.order_by(GreensModel.num.desc()).all()
	people = [
		{	"id": person.id,
			"greens": person.num,
			"name": person.name,
			"lastupdate": (datetime.datetime.utcnow() - person.lastupdate).days
		} for person in sqlQuery]
	if flask.session.get("access_token"):
		return flask.render_template("index.html", greens=flask.session.get("greens"), name=flask.session.get("name"), id=flask.session.get("id"), people=people)		
	else:
		client = Client()
		authorize_url = client.authorization_url(client_id=secrets.client_id, redirect_uri=serverURL+'/authorized',scope="activity:read_all")
		return flask.render_template("index.html", url=authorize_url, people=people)
	
@app.route("/authorized", methods=["GET"])
def authorize_page():
	if flask.request.args.get('error'):
		return flask.redirect("/")
	client = Client()
	code = flask.request.args.get('code') # or whatever your framework does
	token_response = client.exchange_code_for_token(client_id=secrets.client_id, client_secret=secrets.api_key, code=code)
	flask.session['access_token'] = token_response['access_token']
	flask.session['refresh_token'] = token_response['refresh_token']
	flask.session['expires_at'] = token_response['expires_at']
	client.access_token = token_response['access_token']
	client.refresh_token = token_response['refresh_token']
	client.expires_at = token_response['expires_at']
	athlete = client.get_athlete()
	name = athlete.firstname + " " + athlete.lastname
	flask.session['name'] = name
	flask.session['id'] = athlete.id
	return flask.redirect("/greens")

@app.route("/greens", methods=["GET"])
def greens_page():
	if flask.session.get("access_token"):
		# if flask.session.get("greens"):
		# 	greens = flask.session.get("greens")
		# else:
		client = Client()
		client.access_token = flask.session.get("access_token")
		client.refresh_token = flask.session.get('refresh_token')
		client.expires_at = flask.session.get('expires_at')
		greens = 0
		greens = 0
		segments = ["30545810", "30546062", "30546055", "7492562"]
		for segment in segments:
			s = client.get_segment(segment)
			greens += s.athlete_segment_stats.effort_count
		flask.session['greens'] = greens
		print(greens)
		person = GreensModel.query.get(flask.session.get('id'))
		if person:
			person.name = flask.session.get('name')
			person.num = greens
			person.lastupdate = datetime.datetime.utcnow()
			db.session.add(person)
			db.session.commit()
		else:
			newPerson = GreensModel(name=flask.session.get('name'), id=flask.session.get('id'), greens=greens, lastupdate=datetime.datetime.utcnow())
			db.session.add(newPerson)
			db.session.commit()
	return flask.redirect("/")

@app.route("/logout")
def logout_page():
	flask.session.pop('access_token', None)
	flask.session.pop('name', None)
	flask.session.pop('refresh_token', None)
	flask.session.pop('id', None)
	flask.session.pop('greens', None)
	return flask.redirect("/")

@app.route('/favicon.ico')
def favicon():
	return flask.send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
	
	
def create_app():
   return app

if __name__ == '__main__':
	if len(sys.argv) == 2:
		serverURL = sys.argv[1]
	print("Website starting at: "+serverURL)
	serve(app, host='127.0.0.1', port=5000)

