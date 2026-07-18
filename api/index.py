# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
import json
import os
import pandas as pd
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'html'),
    template_folder=os.path.join(BASE_DIR, 'html'),
    static_url_path=''
)
CORS(app)

app.config['SECRET_KEY'] = 'supersecretkey'

# Ensure the instance directory exists for SQLite
instance_dir = os.path.join(BASE_DIR, 'instance')
try:
    os.makedirs(instance_dir, exist_ok=True)
except Exception:
    pass

# Support production databases (PostgreSQL, MySQL, etc.) via environment variable
database_uri = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if database_uri:
    # PostgreSQL compatibility fix for SQLAlchemy (replace postgres:// with postgresql://)
    if database_uri.startswith("postgres://"):
        database_uri = database_uri.replace("postgres://", "postgresql://", 1)
else:
    # Fallback to local SQLite database with normalized path
    # On Vercel, the filesystem is read-only. We write sqlite to the writable '/tmp' directory.
    if os.environ.get('VERCEL'):
        db_path = '/tmp/database.db'
        # Copy the pre-populated database if it exists in the repository
        repo_db_path = os.path.join(instance_dir, 'database.db')
        if not os.path.exists(db_path) and os.path.exists(repo_db_path):
            import shutil
            try:
                shutil.copy2(repo_db_path, db_path)
            except Exception:
                pass
    else:
        db_path = os.path.join(instance_dir, 'database.db').replace('\\', '/')
    database_uri = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Placeholder for login required logic
        return f(*args, **kwargs)
    return decorated_function



# ── Helpers ──────────────────────────────────────────────────────

class questionset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(20))
    date = db.Column(db.String(20))

class student_user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reg_id = db.Column(db.String(50), unique=True)
    dob = db.Column(db.String(100))          # hashed DOB used as password
    plain_dob = db.Column(db.String(50))     # original plain DOB for recovery
    student_name = db.Column(db.String(100))
    student_sem = db.Column(db.String(20))
    s_year = db.Column(db.String(20))

class AppUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    latestScore = db.Column(db.Integer, default=0)
    highScore = db.Column(db.Integer, default=0)
    totalTimeSpent = db.Column(db.Integer, default=0)
    lastLogin = db.Column(db.String(50), default="")
    correct = db.Column(db.Integer, default=0)
    wrong = db.Column(db.Integer, default=0)
    unanswered = db.Column(db.Integer, default=0)
    dailyTime = db.Column(db.JSON, default=dict)
    history = db.Column(db.JSON, default=list)

class QuizData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    startTime = db.Column(db.String(50))
    endTime = db.Column(db.String(50))
    time = db.Column(db.Integer)
    questions = db.Column(db.JSON, default=list)

with app.app_context():
    db.create_all()
    # Auto-seed a default admin user if the database has no users
    try:
        if AppUser.query.first() is None:
            default_admin = AppUser(
                username='admin',
                password='adminpassword',  # Plain text is accepted by login logic for admin/default users
                role='admin'
            )
            db.session.add(default_admin)
            db.session.commit()
            print("[INFO] Seeded default admin user: admin / adminpassword")
    except Exception as e:
        print(f"[ERROR] Failed to seed default user: {e}")




@app.route("/")
def serve_index():
    return app.send_static_file("index.html")

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'css'), filename)


# ── Auth Routes ──────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json()
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # 1. Try to login from AppUser table (plaintext passwords for default / admin users)
    if password:
        user = AppUser.query.filter_by(username=username, password=password).first()
        if user:
            return jsonify({
                "message": "Login successful",
                "user": {
                    "username": user.username,
                    "role":     user.role
                }
            }), 200

    # 2. Try to login from student_user table (allow login with just username, or verify password if provided)
    student = student_user.query.filter_by(reg_id=username).first()
    if student:
        if not password or check_password_hash(student.dob, password):
            return jsonify({
                "message": "Login successful",
                "user": {
                    "username": student.reg_id,
                    "role":     "student"
                }
            }), 200

    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/register", methods=["POST"])
def register():
    body     = request.get_json()
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()
    role     = body.get("role", "student").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if role not in ("student", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    if AppUser.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    new_user = AppUser(username=username, password=password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

# ── Quiz Routes ──────────────────────────────────────────────────

@app.route("/api/quiz", methods=["GET"])
def get_quiz():
    quiz = QuizData.query.first()
    if not quiz:
        return jsonify({"error": "Quiz data not found"}), 404
    data = {
        "startTime": quiz.startTime,
        "endTime": quiz.endTime,
        "time": quiz.time,
        "questions": quiz.questions
    }
    return jsonify(data), 200


@app.route("/api/quiz", methods=["POST"])
def save_quiz():
    """Admin: replace quiz data."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data provided"}), 400
    
    quiz = QuizData.query.first()
    if not quiz:
        quiz = QuizData()
        db.session.add(quiz)
        
    quiz.startTime = body.get("startTime", "")
    quiz.endTime = body.get("endTime", "")
    quiz.time = body.get("time", 0)
    quiz.questions = body.get("questions", [])
    
    # pyrefly: ignore [missing-import]
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(quiz, "questions")
    
    db.session.commit()
    return jsonify({"message": "Quiz saved successfully"}), 200

@app.route("/api/quiz/upload-pdf", methods=["POST"])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(file.stream)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n\n"
            return jsonify({"text": text}), 200
        except ImportError:
            return jsonify({"error": "pypdf is not installed on the server"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400

# ── Results Routes ───────────────────────────────────────────────

@app.route("/api/results", methods=["GET"])
def get_results():
    results = QuizResult.query.all()
    result_dict = {r.username: r for r in results}

    # Build name/sem/year lookup from student_user table
    student_info = {}
    for su in student_user.query.all():
        student_info[su.reg_id] = {
            "student_name": su.student_name or su.reg_id,
            "student_sem":  su.student_sem or "",
            "s_year":       su.s_year or ""
        }

    # Collect every known student username
    all_students = set()
    for u in AppUser.query.filter_by(role='student').all():
        all_students.add(u.username)
    for reg_id in student_info:
        all_students.add(reg_id)
    for username in result_dict.keys():
        all_students.add(username)

    data = {"results": []}
    for username in all_students:
        info = student_info.get(username, {})
        student_name = info.get("student_name", username)
        student_sem  = info.get("student_sem", "")
        s_year       = info.get("s_year", "")

        r = result_dict.get(username)
        if r:
            # Calculate highScoreTime from history
            high_score_time = 0
            if r.history:
                best_score = -1
                best_time = 999999
                for attempt in r.history:
                    s = attempt.get("score", 0)
                    t = attempt.get("timeSpent", 0)
                    if s > best_score:
                        best_score = s
                        best_time = t
                    elif s == best_score and t < best_time:
                        best_time = t
                high_score_time = best_time if best_score != -1 else (r.totalTimeSpent or 0)
            else:
                high_score_time = r.totalTimeSpent or 0

            data["results"].append({
                "username":      r.username,
                "student_name":  student_name,
                "student_sem":   student_sem,
                "s_year":        s_year,
                "latestScore":   r.latestScore,
                "highScore":     r.highScore,
                "totalTimeSpent":r.totalTimeSpent,
                "highScoreTime": high_score_time,
                "lastLogin":     r.lastLogin,
                "correct":       r.correct,
                "wrong":         r.wrong,
                "unanswered":    r.unanswered,
                "dailyTime":     r.dailyTime,
                "history":       r.history
            })
        else:
            data["results"].append({
                "username":      username,
                "student_name":  student_name,
                "student_sem":   student_sem,
                "s_year":        s_year,
                "latestScore":   0,
                "highScore":     0,
                "totalTimeSpent":0,
                "highScoreTime": 0,
                "lastLogin":     "",
                "correct":       0,
                "wrong":         0,
                "unanswered":    0,
                "dailyTime":     {},
                "history":       []
            })
    return jsonify(data), 200


@app.route("/api/results", methods=["POST"])
def save_result():
    """Save / update a single user's quiz result, tracking history for multiple attempts."""
    body     = request.get_json()
    username = (body.get("username") or "").strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    import datetime
    today_str = datetime.date.today().isoformat()
    date_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    time_spent = int(body.get("timeSpent") or 0)
    score_val = int(body.get("score") or 0)
    correct_val = int(body.get("correct") or 0)
    wrong_val = int(body.get("wrong") or 0)
    unans_val = int(body.get("unanswered") or 0)

    new_attempt = {
        "date": date_time_str,
        "score": score_val,
        "timeSpent": time_spent,
        "correct": correct_val,
        "wrong": wrong_val,
        "unanswered": unans_val,
        "answers": body.get("answers", [])
    }

    existing = QuizResult.query.filter_by(username=username).first()

    if existing:
        # Check if the user already has attempts in history for TODAY (daily limit)
        history = list(existing.history) if existing.history else []
        already_attempted_today = False
        for attempt in history:
            attempt_date = attempt.get("date", "")
            if attempt_date.startswith(today_str):
                already_attempted_today = True
                break
        
        if already_attempted_today:
            return jsonify({"message": "Test has already been attempted today. Additional attempts are not recorded."}), 200

        existing.latestScore = score_val
        existing.highScore = max(existing.highScore or 0, score_val)
        existing.totalTimeSpent = (existing.totalTimeSpent or 0) + time_spent
        existing.correct = (existing.correct or 0) + correct_val
        existing.wrong = (existing.wrong or 0) + wrong_val
        existing.unanswered = (existing.unanswered or 0) + unans_val
        existing.lastLogin = date_time_str
        
        # SQLAlchemy JSON columns require reassignment to trigger update
        history.append(new_attempt)
        existing.history = history
        
        daily_time = dict(existing.dailyTime) if existing.dailyTime else {}
        daily_time[today_str] = daily_time.get(today_str, 0) + time_spent
        existing.dailyTime = daily_time
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(existing, "history")
        flag_modified(existing, "dailyTime")
    else:
        new_result = QuizResult(
            username=username,
            latestScore=score_val,
            highScore=score_val,
            totalTimeSpent=time_spent,
            lastLogin=date_time_str,
            correct=correct_val,
            wrong=wrong_val,
            unanswered=unans_val,
            history=[new_attempt],
            dailyTime={today_str: time_spent}
        )
        db.session.add(new_result)

    db.session.commit()
    return jsonify({"message": "Result saved successfully"}), 200


@app.route("/api/results/<username>", methods=["GET"])
def get_user_result(username):
    r = QuizResult.query.filter_by(username=username).first()
    if not r:
        return jsonify({"error": "Result not found"}), 404
    
    record = {
        "username": r.username,
        "latestScore": r.latestScore,
        "highScore": r.highScore,
        "totalTimeSpent": r.totalTimeSpent,
        "lastLogin": r.lastLogin,
        "correct": r.correct,
        "wrong": r.wrong,
        "unanswered": r.unanswered,
        "dailyTime": r.dailyTime,
        "history": r.history
    }
    return jsonify(record), 200


@app.route("/api/results/<username>", methods=["DELETE"])
def delete_user_result(username):
    """Delete a student's quiz results AND their account from student_user."""
    deleted_something = False

    r = QuizResult.query.filter_by(username=username).first()
    if r:
        db.session.delete(r)
        deleted_something = True

    su = student_user.query.filter_by(reg_id=username).first()
    if su:
        db.session.delete(su)
        deleted_something = True

    # Also remove from AppUser if present
    au = AppUser.query.filter_by(username=username).first()
    if au and au.role == 'student':
        db.session.delete(au)
        deleted_something = True

    if not deleted_something:
        return jsonify({"error": "User not found"}), 404

    db.session.commit()
    return jsonify({"message": f"Student {username} deleted successfully"}), 200

# ── Users Routes (Admin) ─────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
def get_users():
    users = AppUser.query.all()
    # Never expose passwords to the client
    safe  = [{"username": u.username, "role": u.role} for u in users]
    return jsonify({"users": safe}), 200


@app.route("/api/users/<username>", methods=["DELETE"])
def delete_user(username):
    user = AppUser.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"User {username} deleted"}), 200


@app.route("/api/bhuvi", methods=["POST"])
@login_required  # Secure this so only logged-in admins can upload files
def import_users():
    # 1. Check if a file was actually uploaded
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    if file:
        try:
            # 2. Read the file using Pandas (handles both CSV and Excel)
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                return jsonify({'status': 'error', 'message': 'Invalid file format. Please upload a CSV or Excel file.'}), 400

            # Normalize column names: strip whitespace and convert to lowercase
            df.columns = [str(c).strip().lower() for c in df.columns]

            # Flexible column name mapping
            reg_id_aliases = ['reg_id', 'regnumber', 'reg_no', 'registration_id', 'roll_no', 'rollno', 'regno']
            name_aliases   = ['name', 'decaler name', 'declarename', 'student_name', 'studentname', 'fullname', 'full_name', 'student name']

            def find_col(df, aliases):
                for alias in aliases:
                    if alias in df.columns:
                        return alias
                return None

            col_reg  = find_col(df, reg_id_aliases)
            col_name = find_col(df, name_aliases)

            missing = []
            if not col_reg:  missing.append('reg_id / regnumber')
            if not col_name: missing.append('name / student_name')
            if missing:
                return jsonify({'status': 'error', 'message': f'Missing required columns: {", ".join(missing)}. Found columns: {list(df.columns)}'}), 400

            # 3. Loop through each row — reg_id is always the password
            imported = []
            skipped  = []

            for index, row in df.iterrows():
                if pd.isna(row[col_reg]) or pd.isna(row[col_name]):
                    continue
                username = str(row[col_reg]).strip()
                student_name = str(row[col_name]).strip()
                if not username or username.lower() in ('nan', 'none', ''):
                    continue
                plain_password = username   # reg_id is the password

                existing_user = student_user.query.filter_by(reg_id=username).first()
                if not existing_user:
                    hashed_pw = generate_password_hash(plain_password, method='pbkdf2:sha256')
                    new_user  = student_user(
                        reg_id=username,
                        dob=hashed_pw,
                        plain_dob=plain_password,
                        student_name=student_name,
                        student_sem='',
                        s_year=''
                    )
                    db.session.add(new_user)
                    imported.append({
                        'name':     student_name,
                        'reg_id':   username,
                        'password': plain_password
                    })
                else:
                    skipped.append(username)

            db.session.commit()
            # Return JSON so the frontend can render the result table
            return jsonify({
                'status':   'success',
                'imported': imported,
                'skipped':  skipped
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'error', 'message': 'Unknown error'}), 400

# ── Forgot Password Route ────────────────────────────────────────

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Return the student's actual password (plain DOB) using their registration number."""
    body   = request.get_json()
    reg_id = (body.get('reg_id') or '').strip()

    if not reg_id:
        return jsonify({'error': 'Registration number is required'}), 400

    student = student_user.query.filter_by(reg_id=reg_id).first()
    if not student:
        return jsonify({'error': 'No account found with this registration number'}), 404

    # plain_dob is stored during Excel import; fall back to hint if missing
    password_text = student.plain_dob if student.plain_dob else None

    return jsonify({
        'message':      'Account found!',
        'student_name': student.student_name,
        'password':     password_text,        # the actual DOB / password
        'has_password': password_text is not None
    }), 200

# ── Health check ─────────────────────────────────────────────────

@app.route('/admin_dashboard')
def admin_dashboard():
    return "Admin Dashboard - Placeholder"

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ── Entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("[OK] Server running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)