from flask import Flask, jsonify, request, make_response
import jwt
import datetime
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

file_path = os.path.abspath(os.getcwd()) + "\database.db"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + file_path
db = SQLAlchemy(app)
app.app_context().push()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(50))
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(50))
    complete = db.Column(db.Boolean)
    user_id = db.Column(db.Integer)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
            print(data)
            current_user = User.query.filter_by(public_id=data['public_id']).first()
            print(current_user)
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated


@app.route('/user', methods=['GET'])
@token_required
def get_all_users(current_user):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that action'})
    users = User.query.all()
    output = []
    for user in users:
        user_data = {'public_id': user.public_id, 'name': user.name, 'password': user.password, 'admin': user.admin}
        output.append(user_data)
    return jsonify({'users': output})


@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user, public_id):
    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found'})
    return jsonify(
        {'user': {'public_id': user.public_id, 'name': user.name, 'password': user.password, 'admin': user.admin}
         })


@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(public_id=str(uuid.uuid4()), name=data['name'], password=hashed_password, admin=False)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'New user created!'})


@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def promote_user(current_user, public_id):
    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found'})
    user.admin = True
    db.session.commit()
    return jsonify({'message': 'The user has been promoted'})


@app.route('/user/<public_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, public_id):
    user = User.query.filter_by(public_id=public_id).first()

    if not user:
        return jsonify({'message': 'No user found'})
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'The user has been deleted'})


@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})

    user = User.query.filter_by(name=auth.username).first()

    if not user:
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode(
            {'public_id': user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
            app.config['SECRET_KEY'])
        print("from login")
        print(token)
        return jsonify({'token': token})

    return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login required"'})


if __name__ == '__main__':
    app.run(debug=True)
