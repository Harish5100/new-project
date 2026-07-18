import os
import json
from index import app, db, AppUser, QuizResult, QuizData

# ── File paths & Helpers for Migration ──────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "users.json")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
QUIZ_FILE  = os.path.join(BASE_DIR, "quiz_data.json")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def migrate():
    with app.app_context():
        print("Starting migration...")
        
        # 1. Migrate Users
        print("Migrating users...")
        users_data = load_json(USERS_FILE)
        for u in users_data.get("users", []):
            if not AppUser.query.filter_by(username=u["username"]).first():
                new_user = AppUser(
                    username=u["username"],
                    password=u["password"],
                    role=u.get("role", "student")
                )
                db.session.add(new_user)
        
        # 2. Migrate Results
        print("Migrating results...")
        results_data = load_json(RESULTS_FILE)
        for r in results_data.get("results", []):
            existing = QuizResult.query.filter_by(username=r["username"]).first()
            if not existing:
                new_result = QuizResult(
                    username=r["username"],
                    latestScore=r.get("latestScore", r.get("score", 0)),
                    highScore=r.get("highScore", r.get("score", 0)),
                    totalTimeSpent=r.get("totalTimeSpent", r.get("timeSpent", 0)),
                    lastLogin=r.get("lastLogin", ""),
                    correct=r.get("correct", 0),
                    wrong=r.get("wrong", 0),
                    unanswered=r.get("unanswered", 0),
                    dailyTime=r.get("dailyTime", {}),
                    history=r.get("history", [])
                )
                db.session.add(new_result)
            else:
                existing.latestScore = r.get("latestScore", r.get("score", 0))
                existing.highScore = r.get("highScore", r.get("score", 0))
                existing.totalTimeSpent = r.get("totalTimeSpent", r.get("timeSpent", 0))
                existing.lastLogin = r.get("lastLogin", "")
                existing.correct = r.get("correct", 0)
                existing.wrong = r.get("wrong", 0)
                existing.unanswered = r.get("unanswered", 0)
                existing.dailyTime = r.get("dailyTime", {})
                existing.history = r.get("history", [])
                
        # 3. Migrate Quiz Data
        print("Migrating quiz data...")
        quiz_data = load_json(QUIZ_FILE)
        if quiz_data:
            existing_quiz = QuizData.query.first()
            if not existing_quiz:
                new_quiz = QuizData(
                    startTime=quiz_data.get("startTime", ""),
                    endTime=quiz_data.get("endTime", ""),
                    time=quiz_data.get("time", 0),
                    questions=quiz_data.get("questions", [])
                )
                db.session.add(new_quiz)
            else:
                existing_quiz.startTime = quiz_data.get("startTime", "")
                existing_quiz.endTime = quiz_data.get("endTime", "")
                existing_quiz.time = quiz_data.get("time", 0)
                existing_quiz.questions = quiz_data.get("questions", [])

        db.session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
