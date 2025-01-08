
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from random import randint, choice
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app)


class UserStats(db.Model):
    userStatsId = db.Column(db.Integer, primary_key=True)
    countGames = db.Column(db.Integer, default=0)
    countWins = db.Column(db.Integer, default=0)
    scoreTotal = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.userId'), nullable=False)


class User(db.Model):
    userId = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    isRegistered = db.Column(db.Boolean, default=True)
    userStats = db.relationship('UserStats', backref='user', uselist=False)
    games = db.relationship('Game', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Game(db.Model):
    gameId = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.userId'), nullable=False)
    game_time = db.Column(db.Integer)
    result = db.Column(db.String(20))
    score = db.Column(db.Integer)

    def generate_random_game_time(self):
        return randint(40, 80)

def calculate_total_score(user):
    """Вычисляет сумму очков для пользователя"""
    total_score = 0
    for game in user.games:
        total_score += game.score
    return total_score

def update_user_stats(user):
    """Обновляет статистику пользователя"""
    user_stats = user.userStats
    user_stats.scoreTotal = calculate_total_score(user)
    user_stats.countGames = len(user.games)
    user_stats.countWins = sum(1 for game in user.games if game.result == 'win')

with app.app_context():
    db.create_all()


@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    user_list = []
    for user in users:
        user_data = {
            "userId": user.userId,
            "email": user.email,
            "login": user.login,
            "isRegistered": user.isRegistered,
            "userStats": {
                "countGames": user.userStats.countGames,
                "countWins": user.userStats.countWins,
                "scoreTotal": user.userStats.scoreTotal
            }
        }
        user_list.append(user_data)
    return jsonify(user_list), 200


@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()

    if not data:
        return jsonify({'message': 'Нет данных в теле запроса'}), 400

    email = data.get('email')
    password = data.get('password')
    login = data.get('login')

    if not all([email, password, login]):
        return jsonify({'message': 'Не все обязательные поля заполнены'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Пользователь с таким email уже существует'}), 400
    if User.query.filter_by(login=login).first():
        return jsonify({'message': 'Пользователь с таким логином уже существует'}), 400

    new_user = User(email=email, login=login)
    new_user.set_password(password)


    new_user_stats = UserStats(user=new_user)
    db.session.add(new_user)
    db.session.add(new_user_stats)
    db.session.commit()
    
    results = ['win', 'lose']
    for _ in range(4):
        random_result = choice(results)
        random_score = randint(100, 250)
        game = Game(user=new_user, result=random_result, score=random_score)
        game.game_time = game.generate_random_game_time()
        db.session.add(game)
    db.session.commit()
    
    update_user_stats(new_user)
    db.session.commit()

    user_data = {
        "userId": new_user.userId,
        "email": new_user.email,
        "login": new_user.login,
        "isRegistered": new_user.isRegistered,
        "userStats": {
            "countGames": new_user_stats.countGames,
            "countWins": new_user_stats.countWins,
            "scoreTotal": new_user_stats.scoreTotal
        }
    }

    return jsonify(user_data), 201


@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()

    if not data:
        return jsonify({'message': 'Нет данных в теле запроса'}), 400

    login = data.get('login')
    password = data.get('password')

    if not all([login, password]):
        return jsonify({'message': 'Не все обязательные поля заполнены'}), 400

    user = User.query.filter_by(login=login).first()

    if user and user.check_password(password):
        user_data = {
            "userId": user.userId,
            "email": user.email,
            "login": user.login,
            "isRegistered": user.isRegistered,
            "userStats": {
                "countGames": user.userStats.countGames,
                "countWins": user.userStats.countWins,
                "scoreTotal": user.userStats.scoreTotal
            }

        }
        return jsonify(user_data), 200
    else:
        return jsonify({'message': 'Неверный логин или пароль'}), 401


@app.route('/add_game', methods=['POST'])
def add_game():
    data = request.get_json()

    if not data:
        return jsonify({'message': 'Нет данных в теле запроса'}), 400

    login = data.get('login')
    result = data.get('result')
    score = data.get('score')

    if not all([login, result, score]):
        return jsonify({'message': 'Не все обязательные поля заполнены'}), 400

    user = User.query.filter_by(login=login).first()

    if not user:
        return jsonify({'message': 'Пользователь не найден'}), 404

    new_game = Game(user=user, result=result, score=score)
    new_game.game_time = new_game.generate_random_game_time()
    db.session.add(new_game)
    db.session.commit()

    update_user_stats(user)
    db.session.commit()
    return jsonify({'message': 'Игра добавлена успешно'}), 201


@app.route('/get_games', methods=['GET'])
def get_games():
    login = request.args.get('login')
    if not login:
        return jsonify({'message': 'Логин обязателен'}), 400
    user = User.query.filter_by(login=login).first()
    if not user:
        return jsonify({'message': 'Пользователь не найден'}), 404

    games = Game.query.filter_by(user_id=user.userId).all()

    games_list = []
    for game in games:
        game_data = {
            "gameId": game.gameId,
            "game_time": game.game_time,
            "result": game.result,
            "score": game.score
        }
        games_list.append(game_data)
    return jsonify(games_list), 200


@app.route('/getAllGames', methods=['GET'])
def get_all_games():
    all_games = []

    for user in User.query.all():
        games = Game.query.filter_by(user_id=user.userId).all()
        for game in games:
            all_games.append({
                "user": user.login,
                "gameId": game.gameId,
                "game_time": game.game_time,
                "result": game.result,
                "score": game.score
            })

    return jsonify(all_games), 200


@app.route('/getAllGamesByLogin', methods=['GET'])
def get_all_games_by_login():
    login = request.args.get('login')
    if not login:
        return jsonify({'message': 'Логин обязателен'}), 400
    user = User.query.filter_by(login=login).first()
    if not user:
        return jsonify({'message': 'Пользователь не найден'}), 404

    games = Game.query.filter_by(user_id=user.userId).all()

    games_list = []
    for game in games:
        game_data = {
            "gameId": game.gameId,
            "game_time": game.game_time,
            "result": game.result,
            "score": game.score
        }
        games_list.append(game_data)
    return jsonify(games_list), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)