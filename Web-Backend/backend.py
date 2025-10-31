from flask import Flask, request, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import os
import uuid
import zipfile
import mimetypes
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
from flask_cors import CORS
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/makros_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE_MB', 100)) * 1024 * 1024

db = SQLAlchemy(app)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    makros = db.relationship('Makro', backref='author', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }

class Makro(db.Model):
    __tablename__ = 'makros'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.Text, nullable=True)
    usecase = db.Column(db.String(200), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)            # relativ zu UPLOAD_FOLDER (inkl. Unterordner)
    preview_filename = db.Column(db.String(255), nullable=True)     # relativ zu UPLOAD_FOLDER (inkl. Unterordner)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'desc': self.desc,
            'usecase': self.usecase,
            'author_id': self.author_id,
            'author_name': self.author.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'preview_url': f"/api/makros/{self.id}/preview" if self.preview_filename else None
        }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

def is_valid_zip(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            return True
    except:
        return False

def _is_preview_member(name: str) -> bool:
    base = os.path.basename(name).lower()
    if not (base.startswith('preview.') or base.startswith('thumb.') or base.startswith('thumbnail.')):
        return False
    ext = os.path.splitext(base)[1]
    return ext in {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm'}

def _save_preview_filestorage(fs, subdir_abs: str, subdir_rel: str) -> str | None:
    if not fs or not getattr(fs, 'filename', ''):
        return None
    base, ext = os.path.splitext(fs.filename.lower())
    if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.mp4', '.webm'}:
        return None
    unique = f"preview{ext}"
    abs_path = os.path.join(subdir_abs, unique)
    fs.save(abs_path)
    return os.path.join(subdir_rel, unique)

def _extract_preview_from_zip(zip_path: str, subdir_abs: str, subdir_rel: str) -> str | None:
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for n in z.namelist():
                if _is_preview_member(n):
                    ext = os.path.splitext(n.lower())[1]
                    rel_name = f"preview{ext}"
                    abs_dest = os.path.join(subdir_abs, rel_name)
                    with z.open(n) as src, open(abs_dest, 'wb') as out:
                        out.write(src.read())
                    return os.path.join(subdir_rel, rel_name)
    except:
        return None
    return None

def _guess_mime(p: str) -> str:
    mt, _ = mimetypes.guess_type(p)
    return mt or 'application/octet-stream'

@app.route('/api/accounts/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    if Account.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    hashed_password = generate_password_hash(data['password'])
    account = Account(name=data['name'], password=hashed_password)
    
    db.session.add(account)
    db.session.commit()
    
    session['account_id'] = account.id
    return jsonify({'message': 'Account created successfully', 'account': account.to_dict()}), 201

@app.route('/api/accounts/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    account = Account.query.filter_by(name=data['name']).first()
    
    if account and check_password_hash(account.password, data['password']):
        session['account_id'] = account.id
        return jsonify({'message': 'Login successful', 'account': account.to_dict()}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/accounts/data', methods=['GET'])
def get_account_data():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    account = Account.query.get(session['account_id'])
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    return jsonify({'account': account.to_dict()}), 200

@app.route('/api/accounts/data', methods=['PUT'])
def update_account_data():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    account = Account.query.get(session['account_id'])
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    data = request.get_json()
    
    if data.get('name'):
        existing = Account.query.filter_by(name=data['name']).first()
        if existing and existing.id != account.id:
            return jsonify({'error': 'Username already exists'}), 409
        account.name = data['name']
    
    if data.get('password'):
        account.password = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({'message': 'Account updated successfully', 'account': account.to_dict()}), 200

@app.route('/api/accounts/logout', methods=['POST'])
def logout():
    session.pop('account_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/makros', methods=['POST'])
def upload_makro():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only ZIP files are allowed'}), 400
    
    name = request.form.get('name')
    desc = request.form.get('desc', '')
    usecase = request.form.get('usecase', '')
    
    base_id = uuid.uuid4().hex
    subdir_rel = base_id
    subdir_abs = os.path.join(app.config['UPLOAD_FOLDER'], subdir_rel)
    os.makedirs(subdir_abs, exist_ok=True)

    safe_orig = secure_filename(file.filename)
    zip_rel = os.path.join(subdir_rel, safe_orig)
    zip_abs = os.path.join(subdir_abs, safe_orig)
    file.save(zip_abs)
    
    if not is_valid_zip(zip_abs):
        try:
            os.remove(zip_abs)
        except FileNotFoundError:
            pass
        try:
            os.rmdir(subdir_abs)
        except OSError:
            pass
        return jsonify({'error': 'Invalid ZIP file'}), 400
    
    try:
        with zipfile.ZipFile(zip_abs, 'r') as z:
            meta_name = None
            for cand in ('meta.json', 'meta/meta.json'):
                if cand in z.namelist():
                    meta_name = cand
                    break
            if meta_name:
                import json
                with z.open(meta_name) as f:
                    meta = json.load(f)
                name = meta.get('name', name) or name
                desc = meta.get('description', meta.get('desc', desc)) or desc
                usecase = meta.get('usecase', meta.get('category', usecase)) or usecase
    except Exception:
        pass
    
    if not name:
        name = os.path.splitext(safe_orig)[0].replace('_', ' ').replace('-', ' ').strip()
    
    preview_filename = None
    preview_fs = request.files.get('preview')
    if preview_fs and preview_fs.filename:
        pf_rel = _save_preview_filestorage(preview_fs, subdir_abs, subdir_rel)
        if pf_rel:
            preview_filename = pf_rel
    if not preview_filename:
        preview_filename = _extract_preview_from_zip(zip_abs, subdir_abs, subdir_rel)
    
    makro = Makro(
        name=name,
        desc=desc,
        usecase=usecase,
        author_id=session['account_id'],
        filename=zip_rel,
        preview_filename=preview_filename
    )
    
    db.session.add(makro)
    db.session.commit()
    
    return jsonify({'message': 'Makro uploaded successfully', 'makro': makro.to_dict()}), 201

@app.route('/api/makros/<int:makro_id>', methods=['GET'])
def get_makro(makro_id):
    makro = Makro.query.get(makro_id)
    if not makro:
        return jsonify({'error': 'Makro not found'}), 404
    return jsonify({'makro': makro.to_dict()}), 200

@app.route('/api/makros/<int:makro_id>/download', methods=['GET'])
def download_makro(makro_id):
    makro = Makro.query.get(makro_id)
    if not makro:
        return jsonify({'error': 'Makro not found'}), 404
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], makro.filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Makro file not found'}), 404
    return send_file(file_path, as_attachment=True, download_name=f"{makro.name}.zip")

@app.route('/api/makros/<int:makro_id>/preview', methods=['GET'])
def preview_makro(makro_id):
    makro = Makro.query.get(makro_id)
    if not makro:
        return jsonify({'error': 'Makro not found'}), 404
    if not makro.preview_filename:
        return jsonify({'error': 'Preview not available'}), 404
    path = os.path.join(app.config['UPLOAD_FOLDER'], makro.preview_filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Preview file not found'}), 404
    return send_file(path, mimetype=_guess_mime(path), as_attachment=False)

@app.route('/api/makros/<int:makro_id>', methods=['PUT'])
def update_makro(makro_id):
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    makro = Makro.query.get(makro_id)
    if not makro:
        return jsonify({'error': 'Makro not found'}), 404
    if makro.author_id != session['account_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if data.get('name'):
        makro.name = data['name']
    if 'desc' in data:
        makro.desc = data['desc']
    if 'usecase' in data:
        makro.usecase = data['usecase']
    
    makro.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Makro updated successfully', 'makro': makro.to_dict()}), 200

@app.route('/api/makros/<int:makro_id>', methods=['DELETE'])
def delete_makro(makro_id):
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    makro = Makro.query.get(makro_id)
    if not makro:
        return jsonify({'error': 'Makro not found'}), 404
    if makro.author_id != session['account_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], makro.filename)
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
    finally:
        pass
    if makro.preview_filename:
        prev_path = os.path.join(app.config['UPLOAD_FOLDER'], makro.preview_filename)
        try:
            if os.path.exists(prev_path):
                os.remove(prev_path)
        finally:
            pass
    try:
        subdir = os.path.dirname(zip_path)
        if os.path.isdir(subdir) and not os.listdir(subdir):
            os.rmdir(subdir)
    except OSError:
        pass
    
    db.session.delete(makro)
    db.session.commit()
    return jsonify({'message': 'Makro deleted successfully'}), 200

@app.route('/api/marketplace', methods=['GET'])
def get_all_makros():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    makros = Makro.query.order_by(Makro.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'makros': [makro.to_dict() for makro in makros.items],
        'total': makros.total,
        'pages': makros.pages,
        'current_page': makros.page
    }), 200

@app.route('/api/marketplace/random', methods=['GET'])
def get_random_makros():
    count = request.args.get('count', 10, type=int)
    count = min(count, 50)
    makros = Makro.query.order_by(db.func.random()).limit(count).all()
    return jsonify({
        'makros': [makro.to_dict() for makro in makros]
    }), 200

@app.route('/api/marketplace/search', methods=['GET'])
def search_makros():
    query = request.args.get('q', '')
    usecase = request.args.get('usecase', '')
    author = request.args.get('author', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    makros_query = Makro.query
    if query:
        makros_query = makros_query.filter(
            db.or_(
                Makro.name.ilike(f'%{query}%'),
                Makro.desc.ilike(f'%{query}%')
            )
        )
    if usecase:
        makros_query = makros_query.filter(Makro.usecase.ilike(f'%{usecase}%'))
    if author:
        makros_query = makros_query.join(Account).filter(Account.name.ilike(f'%{author}%'))
    
    per_page = min(per_page, 100)
    makros = makros_query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'makros': [makro.to_dict() for makro in makros.items],
        'total': makros.total,
        'pages': makros.pages,
        'current_page': makros.page
    }), 200

@app.route('/api/my-makros', methods=['GET'])
def get_my_makros():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    makros = Makro.query.filter_by(author_id=session['account_id']).order_by(
        Makro.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'makros': [makro.to_dict() for makro in makros.items],
        'total': makros.total,
        'pages': makros.pages,
        'current_page': makros.page
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

with app.app_context():
    db.create_all()
    try:
        db.session.execute(text("ALTER TABLE makros ADD COLUMN IF NOT EXISTS preview_filename VARCHAR(255)"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    print("Database tables created successfully!")

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(
        debug=debug_mode, 
        host=os.getenv('FLASK_HOST', '0.0.0.0'), 
        port=int(os.getenv('FLASK_PORT', 5000))
    )
