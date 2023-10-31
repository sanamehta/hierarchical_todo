#importing all libraries
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash


# Initialize Flask app
app = Flask(__name__)

# Configuration for the SQLAlchemy database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.secret_key = '1234'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# Initialize SQLAlchemy with Flask app
db = SQLAlchemy(app)


# Initialize Flask-Login's login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




#Objects 

# User model definition
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# Todo model definition
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    complete = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('todo.id'), nullable=True)
    sub_tasks = db.relationship('Todo', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade='all, delete-orphan')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Form for user registration
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

# Form for user login
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')




# Routes

# Route for the main index page displaying tasks
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('register'))  # Redirect to registration page if not authenticated
    todos = Todo.query.filter_by(user_id=current_user.id, parent_id=None).all()
    return render_template('index.html', todos=todos)

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    elif form.is_submitted():
        flash('There was an error with your registration', 'danger')
    return render_template('register.html', title='Register', form=form)
   


# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)


# Route for logging out
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Route for adding a new task
@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    title = request.form.get('title')
    parent_id = request.form.get('parent_id')
    if not title:
        return redirect(url_for('index'))
    new_task = Todo(title=title, user_id=current_user.id)
    if parent_id:
        new_task.parent_id = parent_id
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('index'))


# Route for editing a task
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return redirect(url_for('index'))

    if request.method == 'POST':
        task.title = request.form.get('title')
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('edit_task.html', task=task)


# Route for deleting a task
@app.route('/delete_task/<int:task_id>', methods=['GET','POST'])
@login_required
def delete_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return redirect(url_for('index'))
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))


# Route for moving a task to a different parent
@app.route('/move_task/<int:task_id>', methods=['GET','POST'])
@login_required
def move_task(task_id):
    new_parent_id = request.form.get('new_parent_id')
    task = Todo.query.get(task_id)
    if task is None:
        return redirect(url_for('index'))  
    try:
        task.parent_id = new_parent_id  
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        
    return redirect(url_for('index')) 




# Main entry point for running the app
if __name__ == "__main__":
    with app.app_context():
        # Create database tables
        db.create_all()
    app.run(debug=True, port=5000)
