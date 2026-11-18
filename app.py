from flask import Flask , render_template , request , redirect , url_for , session , flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "exam_portal_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///exam_portal.db'
db = SQLAlchemy(app)


@app.template_filter('active_check')
def active_check(user_id):
    u = db.session.get(User , user_id)
    return u.is_active if u else False



class User(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    email = db.Column(db.String(120) , unique=True , nullable=False)
    password = db.Column(db.String(60) , nullable=False)
    role = db.Column(db.String(20) , nullable=False)
    is_active = db.Column(db.Boolean() , default=True)


class Examiner(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    user_id = db.Column(db.Integer , db.ForeignKey('user.id') , nullable=False)
    name = db.Column(db.String(60) , nullable=False)
    examiner_code = db.Column(db.Integer , nullable=False)
    department = db.Column(db.String(60) , nullable=False)
    contact_details = db.Column(db.String(60) , nullable=False)
    is_approved = db.Column(db.Boolean() , default=False)


class Student(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    user_id = db.Column(db.Integer , db.ForeignKey('user.id') , nullable=False)
    name = db.Column(db.String(60) , nullable=False)
    roll_no = db.Column(db.String(30) , nullable=False)
    department = db.Column(db.String(60) , nullable=False)
    contact_details = db.Column(db.String(60) , nullable=False)


class Course(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    course_code = db.Column(db.String(20) , unique=True , nullable=False)
    course_name = db.Column(db.String(100) , nullable=False)
    department = db.Column(db.String(60) , nullable=False)
    description = db.Column(db.String(250) , nullable=True)


class Exam(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id') , nullable=False)
    assigned_examiner_id = db.Column(db.Integer , db.ForeignKey('examiner.id') , nullable=False)
    exam_title = db.Column(db.String(100) , nullable=False)
    exam_date = db.Column(db.DateTime , nullable=False)
    duration = db.Column(db.String(40) , nullable=False)
    total_seats = db.Column(db.Integer , nullable=False)
    available_seats = db.Column(db.Integer , nullable=False)
    status = db.Column(db.String(30) , default='Open')  # Open, Scheduled, Completed

    course = db.relationship('Course' , backref=db.backref('exams' , lazy=True))
    examiner = db.relationship('Examiner' , backref=db.backref('exams' , lazy=True))


class Rubric(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id') , nullable=False)
    criteria_name = db.Column(db.String(100) , nullable=False)
    max_marks = db.Column(db.Integer , nullable=False)

    exam = db.relationship('Exam' , backref=db.backref('rubrics' , lazy=True))


class Booking(db.Model):
    id = db.Column(db.Integer , primary_key=True)
    exam_id = db.Column(db.Integer , db.ForeignKey('exam.id') , nullable=False)
    user_id = db.Column(db.Integer , db.ForeignKey('user.id') , nullable=False)
    booking_date = db.Column(db.DateTime , default=datetime.utcnow)
    status = db.Column(db.String(30) , default='Booked')
    marks_obtained = db.Column(db.Float , nullable=True)
    remarks = db.Column(db.String(200) , nullable=True)

    exam = db.relationship('Exam' , backref=db.backref('bookings', lazy=True))
    user = db.relationship('User' , backref=db.backref('bookings', lazy=True))



@app.route("/")
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == "student" :
            return redirect(url_for('student_dashboard'))
        elif role == "examiner" :
            return redirect(url_for('examiner_dashboard'))
        elif role == "admin" :
            return redirect(url_for('admin_dashboard'))
        session.clear()
    return redirect(url_for('login'))


@app.route("/register" , methods = ['GET' , 'POST'])
def register():
    if request.method == 'POST' :
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        fullname = request.form.get('name')
        department = request.form.get('department' , 'General')
        contact_details = request.form.get('contact_details' , 'None')

        if not email or not password or not role:
            flash(" Please fill all  fields ! ")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash(" E-mail is already in use .")
            return redirect(url_for('register'))

        new_user = User(email=email , password=password , role=role , is_active=True)
        db.session.add(new_user)
        db.session.commit()

        if role == "student":
            student = Student(
                user_id=new_user.id ,
                name=fullname ,
                roll_no=request.form.get('roll_no' , f"STU{new_user.id}"),
                department=department ,
                contact_details=contact_details
            )
            db.session.add(student)
            db.session.commit()
            flash(" This student is registered successfully ! Please proceed to login .")
            return redirect(url_for('login'))

        elif role == "examiner":
            examiner = Examiner(
                user_id=new_user.id ,
                name=fullname ,
                examiner_code=int(datetime.utcnow().timestamp() % 10000) ,
                department=department ,
                contact_details=contact_details ,
                is_approved=False
            )
            db.session.add(examiner)
            db.session.commit()
            flash(" Examiner registered! Waiting for Admin approval.")
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route("/login" , methods=['GET' , 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user or user.password != password:
            flash(" Invalid e-mail or password .")
            return redirect(url_for('login'))
        if not user.is_active:
            flash(" This account has been deactivated/blacklisted .")
            return redirect(url_for('login'))
        if user.role == 'examiner':
            examiner_profile = Examiner.query.filter_by(user_id=user.id).first()
            if not examiner_profile or not examiner_profile.is_approved:
                flash(" Access is currently denied. Waiting for admin approval .")
                return redirect(url_for('login'))

        session['user_id'] = user.id
        session['email'] = user.email
        session['role'] = user.role
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route("/logout")
def logout():
    session.clear()
    flash(" You have been logged out.")
    return redirect(url_for('login'))



@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    search_query = request.args.get('search_query', '').strip()
    if search_query:

        courses = Course.query.filter(
            Course.course_name.contains(search_query) | Course.course_code.contains(search_query)).all()
        exams = Exam.query.filter(Exam.exam_title.contains(search_query) | Exam.id.like(f"%{search_query}%")).all()
        examiners = Examiner.query.filter(
            Examiner.name.contains(search_query) | Examiner.id.like(f"%{search_query}%")).all()
        students = Student.query.filter(
            Student.name.contains(search_query) | Student.roll_no.contains(search_query) | Student.id.like(
                f"%{search_query}%")).all()
        bookings = Booking.query.filter(Booking.id.like(f"%{search_query}%")).all()
    else:
        courses = Course.query.all()
        exams = Exam.query.all()
        examiners = Examiner.query.all()
        students = Student.query.all()
        bookings = Booking.query.all()

    return render_template(
        'admin_dashboard.html',
        total_courses=Course.query.count(),
        total_exams=Exam.query.count(),
        total_examiners=Examiner.query.count(),
        total_students=Student.query.count(),
        total_bookings=Booking.query.count(),
        courses=courses,
        exams=exams,
        examiners=examiners,
        students=students,
        bookings=bookings
    )


@app.route('/admin_add_course', methods=['GET', 'POST'])
def admin_add_course():
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    if request.method == 'POST':
        course = Course(
            course_code=request.form.get('course_code'),
            course_name=request.form.get('course_name'),
            department=request.form.get('department'),
            description=request.form.get('description')
        )
        db.session.add(course)
        db.session.commit()
        flash("Course created successfully!")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_add_course.html')


@app.route('/admin_edit_course/<int:id>', methods=['GET', 'POST'])
def admin_edit_course(id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    course = Course.query.get_or_404(id)
    if request.method == 'POST':
        course.course_code = request.form.get('course_code')
        course.course_name = request.form.get('course_name')
        course.department = request.form.get('department')
        course.description = request.form.get('description')
        db.session.commit()
        flash("Course updated successfully!")
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_course.html', course=course)


@app.route('/admin_delete_course/<int:id>')
def admin_delete_course(id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    course = Course.query.get_or_404(id)
    db.session.delete(course)
    db.session.commit()
    flash("Course removed successfully!")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin_add_exam', methods=['GET', 'POST'])
def admin_add_exam():
    if session.get('role') != 'admin':
        return " Unauthorized " , 403
    if request.method == 'POST':
        seats = int(request.form.get('total_seats'))
        exam = Exam(
            course_id=int(request.form.get('course_id')) ,
            assigned_examiner_id=int(request.form.get('assigned_examiner_id')) ,
            exam_title=request.form.get('exam_title') ,
            exam_date=datetime.strptime(request.form.get('exam_date') , '%Y-%m-%d') ,
            duration=request.form.get('duration') ,
            total_seats=seats ,
            available_seats=seats ,
            status=request.form.get('status' , 'Open')
        )
        db.session.add(exam)
        db.session.commit()
        flash("Examination scheduled successfully!")
        return redirect(url_for('admin_dashboard'))
    courses = Course.query.all()
    examiners = Examiner.query.filter_by(is_approved=True).all()
    return render_template('admin_add_exam.html', courses=courses , examiners=examiners)


@app.route('/admin_edit_exam/<int:id>' , methods=['GET' , 'POST'])
def admin_edit_exam(id):
    if session.get('role') != 'admin':
        return " Unauthorized " , 403
    exam = Exam.query.get_or_404(id)
    if request.method == 'POST':
        exam.exam_title = request.form.get('exam_title')
        exam.course_id = int(request.form.get('course_id'))
        exam.assigned_examiner_id = int(
            request.form.get('assigned_examiner_id'))
        exam.exam_date = datetime.strptime(request.form.get('exam_date'), '%Y-%m-%d')
        exam.duration = request.form.get('duration')

        new_seats = int(request.form.get('total_seats'))
        exam.total_seats = new_seats
        exam.available_seats = new_seats
        exam.status = request.form.get('status')

        db.session.commit()
        flash("Examination configuration and timeline updated successfully!")
        return redirect(url_for('admin_dashboard'))
    courses = Course.query.all()
    examiners = Examiner.query.all()
    return render_template('admin_edit_exam.html' , exam=exam , courses=courses , examiners=examiners)


@app.route('/admin_delete_exam/<int:id>')
def admin_delete_exam(id):
    if session.get('role') != 'admin':
        return " Unauthorized ", 403
    exam = Exam.query.get_or_404(id)
    Booking.query.filter_by(exam_id=exam.id).delete()
    Rubric.query.filter_by(exam_id=exam.id).delete()
    db.session.delete(exam)
    db.session.commit()
    flash(" Examination removed successfully! ")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin_manage_rubrics/<int:exam_id>', methods=['GET' , 'POST'])
def admin_manage_rubrics(exam_id):
    if session.get('role') != 'admin':
        return " Unauthorized ", 403
    exam = Exam.query.get_or_404(exam_id)
    if request.method == 'POST':
        criteria_name = request.form.get('criteria_name')
        max_marks = int(request.form.get('max_marks'))
        rubric = Rubric(exam_id=exam.id, criteria_name=criteria_name , max_marks=max_marks)
        db.session.add(rubric)
        db.session.commit()
        flash("Rubric criteria added successfully!")
        return redirect(url_for('admin_manage_rubrics' , exam_id=exam.id))
    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    return render_template('admin_manage_rubrics.html' , exam=exam ,  rubrics=rubrics)


@app.route('/admin_delete_rubric/<int:id>')
def admin_delete_rubric(id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    rubric = Rubric.query.get_or_404(id)
    exam_id = rubric.exam_id
    db.session.delete(rubric)
    db.session.commit()
    flash("Rubric criteria removed.")
    return redirect(url_for('admin_manage_rubrics' , exam_id=exam_id))


@app.route('/admin_toggle_exam_status/<int:id>/<string:status>')
def admin_toggle_exam_status(id , status):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    exam = Exam.query.get_or_404(id)
    exam.status = status
    db.session.commit()
    flash(f" Exam slots and student booking status changed to {status}! ")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin_reschedule_booking/<int:id>', methods=['GET', 'POST'])
def admin_reschedule_booking(id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403
    booking = Booking.query.get_or_404(id)
    if request.method == 'POST':
        new_exam_id = int(request.form.get('new_exam_id'))
        if booking.exam_id != new_exam_id:
            old_exam = Exam.query.get(booking.exam_id)
            new_exam = Exam.query.get(new_exam_id)
            if new_exam and new_exam.available_seats > 0:
                old_exam.available_seats += 1
                new_exam.available_seats -= 1
                booking.exam_id = new_exam_id
                db.session.commit()
                flash("Student booking successfully rescheduled!")
            else:
                flash("Selected exam has no available seats.")
        return redirect(url_for('admin_dashboard'))
    exams = Exam.query.filter_by(status='Open').all()
    return render_template('admin_reschedule_booking.html', booking=booking, exams=exams)


@app.route('/admin_action/<string:target>/<int:id>/<string:act>')
def admin_action(target, id, act):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    if target == 'examiner':
        examiner = Examiner.query.get_or_404(id)
        linked_user = User.query.get(examiner.user_id)
        if act in ['approve', 'unblacklist']:
            examiner.is_approved = True
            if linked_user:
                linked_user.is_active = True
        elif act == 'blacklist':
            examiner.is_approved = False
            if linked_user:
                linked_user.is_active = False

    elif target == 'user':
        user = User.query.get_or_404(id)
        user.is_active = (act == 'unblacklist')

    db.session.commit()
    flash("Examiner/User status updated successfully!")
    return redirect(url_for('admin_dashboard'))


@app.route('/examiner_dashboard')
def examiner_dashboard():
    if session.get('role') != 'examiner':
        return " Unauthorized " , 403
    examiner = Examiner.query.filter_by(user_id=session.get('user_id')).first_or_404()
    assigned_exams = Exam.query.filter_by(assigned_examiner_id=examiner.id).all()
    return render_template('examiner_dashboard.html' , examiner=examiner , assigned_exams=assigned_exams)


@app.route('/examiner_manage_exam/<int:id>', methods=['GET', 'POST'])
def examiner_manage_exam(id):
    if session.get('role') != 'examiner':
        return "Unauthorized", 403
    examiner = Examiner.query.filter_by(user_id=session.get('user_id')).first_or_404()
    exam = Exam.query.get_or_404(id)

    if exam.assigned_examiner_id != examiner.id:
        return " Unauthorized Exam Access " , 403

    if request.method == 'POST':
        action_type = request.form.get('action_type')
        if action_type == 'add_rubric' :
            rubric = Rubric(
                exam_id=exam.id ,
                criteria_name=request.form.get('criteria_name') ,
                max_marks=int(request.form.get('max_marks'))
            )
            db.session.add(rubric)
            flash(" Rubric criteria added. ")
        elif action_type == 'grade_student':
            booking_id = int(request.form.get('booking_id'))
            booking = Booking.query.get_or_404(booking_id)
            booking.marks_obtained = float(request.form.get('marks_obtained'))
            booking.remarks = request.form.get('remarks')
            booking.status = 'Completed'
            flash(" Student marks updated. ")
        elif action_type == 'complete_exam':
            exam.status = 'Completed'
            flash(" Exam Ended. ")

        db.session.commit()
        return redirect(url_for('examiner_manage_exam' , id=exam.id))

    bookings = Booking.query.filter_by(exam_id=exam.id).all()
    rubrics = Rubric.query.filter_by(exam_id=exam.id).all()
    return render_template('examiner_manage_exam.html' , exam=exam , bookings=bookings , rubrics=rubrics)


# -------------------- STUDENT ROUTES --------------------

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return " Unauthorized " , 403
    user_id = session.get('user_id')
    student = Student.query.filter_by(user_id=user_id).first_or_404()
    available_exams = Exam.query.filter(Exam.status == 'Open').all()
    my_bookings = Booking.query.filter_by(user_id=user_id).all()
    return render_template('student_dashboard.html' , student=student , available_exams=available_exams , my_bookings=my_bookings)


@app.route('/book_exam/<int:id>')
def book_exam(id):
    if session.get('role') != 'student':
        return "Unauthorized" , 403
    user_id = session.get('user_id')
    exam = Exam.query.get_or_404(id)

    if exam.status != 'Open' or exam.available_seats <= 0:
        flash(" Exam is closed or no seats available. ")
        return redirect(url_for('student_dashboard'))

    existing = Booking.query.filter_by(user_id=user_id , exam_id=exam.id).first()
    if existing:
        flash(" You have already booked this exam slot. ")
        return redirect(url_for('student_dashboard'))

    exam.available_seats -= 1
    booking = Booking(user_id=user_id , exam_id=exam.id , status='Booked')
    db.session.add(booking)
    db.session.commit()
    flash(f" Successfully booked seat for {exam.exam_title}!")
    return redirect(url_for('student_dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True , port=8000)