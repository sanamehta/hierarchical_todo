from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.secret_key = '1234'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    complete = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('todo.id'), nullable=True)
    sub_tasks = db.relationship('Todo', backref=db.backref('parent', remote_side=[id]), lazy='dynamic', cascade='all, delete-orphan')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@app.route('/home')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('home.html')


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
    return render_template('register.html', title='Register', form=form)

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

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    title = request.form.get('title')
    parent_id = request.form.get('parent_id')
    if not title:
        flash('Task title is required!', 'danger')
        return redirect(url_for('index'))
    new_task = Todo(title=title, user_id=current_user.id)
    if parent_id:
        new_task.parent_id = parent_id
    db.session.add(new_task)
    db.session.commit()
    flash('Task added successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    todos = Todo.query.filter_by(user_id=current_user.id, parent_id=None).all()  # Display only the tasks of the current user
    return render_template('index.html', todos=todos)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Unauthorized to edit this task.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        task.title = request.form.get('title')
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit_task.html', task=task)

@app.route('/delete_task/<int:task_id>', methods=['GET','POST'])
@login_required
def delete_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Unauthorized to delete this task.', 'danger')
        return redirect(url_for('index'))
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/move_task/<int:task_id>', methods=['GET','POST'])
@login_required
def move_task(task_id):
    new_parent_id = request.form.get('new_parent_id')

    # Assuming you have a Task model with an id and parent_id fields
    # And assuming you have a TodoList model where each TodoList has multiple tasks
    task = Todo.query.get(task_id)
    if task is None:
        flash('Task not found!', 'error')
        return redirect(url_for('index'))  # Replace 'index' with your view function that displays tasks

    try:
        task.parent_id = new_parent_id  # Update parent_id to the new list's id
        db.session.commit()
        flash('Task moved successfully!', 'success')
    except Exception as e:
        flash('Error moving task: ' + str(e), 'error')
        db.session.rollback()
        
    return redirect(url_for('index')) 

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8007)
