import config
import openai
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
db = SQLAlchemy(app)


CORS(app)
cors = CORS(app, resources={r"/": {"origins": ""}})


openai.api_key = config.OPENAI_API_KEY


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_info = db.Column(db.Text, nullable=False)
    preferences = db.Column(db.Text, nullable=True)
    schedule_text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='schedules')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    schedules = db.relationship('Schedule', back_populates='user')


with app.app_context():
    db.create_all()


@app.route('/generate-trip', methods=["POST", "GET"])
def generate_trip():
    if request.method == "POST":
        data = request.get_json()
        prompt = data.get("prompt")
        preferences = data.get("preferences")
    elif request.method == "GET":
        prompt = request.args.get("prompt")
        preferences = request.args.get("preferences")

    user_prompt_with_graph = f"Generate a trip schedule for {prompt}. Include time stamps for each activity and include specific locations"
    if preferences:
        user_prompt_with_graph += f" My preferences are: {preferences}"

    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=user_prompt_with_graph,
            max_tokens=700,
            temperature=0.7,
        )
        generated_schedule = response['choices'][0]['text']
        return jsonify({"generated_schedule": generated_schedule})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/add-schedule', methods=["POST"])
def add_schedule():
    if request.method == "POST":
        try:
            data = request.get_json()
            schedule_text = data.get("schedule_text")
            trip_info = data.get("trip_info")
            preferences = data.get("preferences")
            user_id = request.headers.get('User-ID')
            new_schedule = Schedule(
                schedule_text=schedule_text, trip_info=trip_info, preferences=preferences, user_id=user_id)
            db.session.add(new_schedule)
            db.session.commit()
            return jsonify({"message": "Schedule added successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif request.method == "GET":
        # Handle GET request logic here, if needed
        return jsonify({"message": "GET request for add-schedule route"})


@app.route('/get-schedules', methods=["GET", "POST"])
def get_schedules():
    try:
        user_id = request.headers.get('User-ID')
        schedules = Schedule.query.filter_by(user_id=user_id).all()
        schedules = [{"id": schedule.id, "trip_info": schedule.trip_info, "preferences": schedule.preferences,
                      "schedule_text": schedule.schedule_text} for schedule in schedules]
        return jsonify({"schedules": schedules})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/delete-schedule/<int:schedule_id>', methods=["DELETE"])
def delete_schedule(schedule_id):
    try:
        schedule = Schedule.query.get(schedule_id)
        if schedule:
            db.session.delete(schedule)
            db.session.commit()
            return jsonify({"message": "Schedule deleted successfully"})
        else:
            return jsonify({"message": "Schedule not found"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
