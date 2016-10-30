from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from flask import (Flask, render_template,
                   request, redirect,
                   jsonify, url_for, flash)

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

from setup import *

app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

db_session = sessionmaker(bind=engine)()

# JSON APIs to view Restaurant Information


@app.route('/category/<int:category_id>/JSON')
def categoryJSON(category_id):
    category = db_session.query(Category).filter_by(id=category_id).one()
    return jsonify(Category=[category.serialize])


@app.route('/categories/JSON')
def categoriesJSON():
    categories = db_session.query(Category).all()
    return jsonify(categories=[i.serialize for i in categories])


@app.route('/category/<int:category_id>/items/JSON')
def categoryItemsJSON(category_id):
    category = db_session.query(Category).filter_by(id=category_id).one()
    items = db_session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/items/JSON')
def ItemsJSON():
    items = db_session.query(Item).all()
    return jsonify(all_items=[i.serialize for i in items])


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']

    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['id'] = data["id"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign in our
    # token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['id'] = user_id

    login_session['provider'] = 'facebook'
    login_session['isLoggedIn'] = True

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session['username']
    del login_session['email']
    del login_session['id']
    del login_session['picture']
    del login_session['provider']
    login_session['isLoggedIn'] = None
    return redirect(url_for('showLogin'))

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        print "Failed to upgrade the authorization code"
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps("Current user is already connected."), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session["picture"] = data["picture"]
    login_session["id"] = data["id"]

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)

    login_session['id'] = user_id
    login_session['isLoggedIn'] = True
    login_session['provider'] = 'google'

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['credentials'].access_token
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']

    if access_token is None:
        print 'Access Token is None'
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['id']
        del login_session['picture']
        del login_session['provider']
        login_session['isLoggedIn'] = None
        return redirect(url_for('showLogin'))
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Create anti-forgery state token

@app.route('/login')
def showLogin():
    if login_session.get('isLoggedIn') != None:
        return redirect(url_for('init'))
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state, provider=login_session.get('provider'), isLoggedIn=login_session.get('isLoggedIn'))

@app.route('/')
def init():
    categories = db_session.query(Category).all()
    return render_template('index.html', categories=categories, provider=login_session.get('provider'), isLoggedIn=login_session.get('isLoggedIn'))

@app.route('/items/')
def allItems():
    items = db_session.query(Item).all()
    return render_template('item.html', items=items, provider=login_session.get('provider'), isLoggedIn=login_session.get('isLoggedIn'))

@app.route('/category/<int:category_id>/items/')
def categoryDetails(category_id):
    category = db_session.query(Category).filter_by(id=category_id).one()
    items = db_session.query(Item).filter_by(
        category_id=category_id).all()
    return render_template('category-details.html',
                           items=items,
                           category=category,
                           isLoggedIn=login_session.get('isLoggedIn'),
                           currentUser=login_session.get('id'),
                           provider=login_session.get('provider'))

@app.route('/category/<int:category_id>/items/new', methods=['GET', 'POST'])
def newItem(category_id):
    if login_session.get('isLoggedIn') == None:
        return redirect(url_for('showLogin'))
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       thumbnail_url=request.form['thumbnail_url'],
                       category_id=category_id,
                       user_id=login_session['id'])
        db_session.add(newItem)
        db_session.commit()

        return redirect(url_for('categoryDetails', category_id=category_id))
    else:
        return render_template('newItem.html', provider=login_session.get('provider'), category_id=category_id,
                               isLoggedIn=login_session.get('isLoggedIn'))

@app.route('/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    item = db_session.query(Item).filter_by(id=item_id).one()
    if login_session.get('isLoggedIn') == None:
        return redirect(url_for('showLogin'))
    if item.user_id != login_session['id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this Item.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.thumbnail_url = request.form['thumbnail_url']

        db_session.add(item)
        db_session.commit()

        flash('Category Successfully Edited %s' % item.name)

        return redirect(url_for('categoryDetails', category_id=category_id))
    else:
        return render_template('edit-item.html',
                               item=item, category_id=category_id,
                               provider=login_session.get('provider'),
                               isLoggedIn=login_session.get('isLoggedIn'))


@app.route('/category/<int:category_id>/item/<int:item_id>/remove',
           methods=['GET', 'POST'])
def removeItem(category_id, item_id):
    item = db_session.query(Item).filter_by(id=item_id).one()
    if login_session.get('isLoggedIn') == None:
        return redirect(url_for('showLogin'))
    if item.user_id != login_session['id']:
        return "<script>function myFunction() {alert('You are not authorized to Remove this Item.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        db_session.delete(item)
        db_session.commit()
        flash('%s Successfully Deleted' % item.name)
        return redirect(url_for('categoryDetails', category_id=category_id))
    else:
        return render_template('remove-item.html', item=item,
                               item_id=item_id, category_id=category_id,
                               provider=login_session.get('provider'),
                               isLoggedIn=login_session.get('isLoggedIn'))

# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], id=login_session[
                   'id'], email=login_session['email'], picture=login_session['picture'])
    db_session.add(newUser)
    db_session.commit()
    user = db_session.query(User).filter_by(id=login_session['id']).one()
    return user.id

def getUserInfo(user_id):
    user = db_session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = db_session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
