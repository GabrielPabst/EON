from flask import Flask, request, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import os
import uuid
import zipfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
from flask_cors import CORS
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)


# Configuration from environment variables with fallbacks
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/makros_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE_MB', 100)) * 1024 * 1024

# Initialize extensions
db = SQLAlchemy(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
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
    filename = db.Column(db.String(255), nullable=False)
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
            'updated_at': self.updated_at.isoformat()
        }

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

def is_valid_zip(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            return True
    except:
        return False

# Account Routes
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

# Makro Routes
@app.route('/api/makros', methods=['POST'])
def upload_makro():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only ZIP files are allowed'}), 400
    
    # Get makro metadata
    name = request.form.get('name')
    desc = request.form.get('desc', '')
    usecase = request.form.get('usecase', '')
    
    if not name:
        return jsonify({'error': 'Makro name is required'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)
    
    # Validate ZIP file
    if not is_valid_zip(file_path):
        os.remove(file_path)
        return jsonify({'error': 'Invalid ZIP file'}), 400
    
    # Create makro record
    makro = Makro(
        name=name,
        desc=desc,
        usecase=usecase,
        author_id=session['account_id'],
        filename=unique_filename
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
    
    # Delete file from filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], makro.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database
    db.session.delete(makro)
    db.session.commit()
    
    return jsonify({'message': 'Makro deleted successfully'}), 200

# Marketplace Routes
@app.route('/api/marketplace', methods=['GET'])
def get_all_makros():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit per_page to prevent abuse
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
    count = min(count, 50)  # Limit to prevent abuse
    
    makros = Makro.query.order_by(db.func.random()).limit(count).all()
    
    return jsonify({
        'makros': [makro.to_dict() for makro in makros]
    }), 200

@app.route('/api/marketplace/search', methods=['GET'])
def search_makros():
    # Get query parameters
    query = request.args.get('q', '')
    usecase = request.args.get('usecase', '')
    author = request.args.get('author', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build base query
    makros_query = Makro.query
    
    # Apply filters
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
    
    # Paginate results
    per_page = min(per_page, 100)  # Limit per_page to prevent abuse
    makros = makros_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'makros': [makro.to_dict() for makro in makros.items],
        'total': makros.total,
        'pages': makros.pages,
        'current_page': makros.page
    }), 200

# User's own makros
@app.route('/api/my-makros', methods=['GET'])
def get_my_makros():
    if 'account_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    per_page = min(per_page, 100)  # Limit per_page to prevent abuse
    
    makros = Makro.query.filter_by(author_id=session['account_id']).order_by(
        Makro.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'makros': [makro.to_dict() for makro in makros.items],
        'total': makros.total,
        'pages': makros.pages,
        'current_page': makros.page
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

# Initialize database
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(
        debug=debug_mode, 
        host=os.getenv('FLASK_HOST', '0.0.0.0'), 
        port=int(os.getenv('FLASK_PORT', 5000))
    )
