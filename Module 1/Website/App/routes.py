from flask import Blueprint, render_template

main = Blueprint('main', __name__)


@main.route('/')
def home():
    return render_template('base.html')


@main.route('/Contact')
def contact():
    return render_template('contact.html')


@main.route('/Projects and Publications')
def projects():
    return render_template('projects.html')