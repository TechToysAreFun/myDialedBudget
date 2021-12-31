import os
import secrets
from PIL import Image
from flask import flash, redirect, render_template, request, session, url_for
from flask_mail import Message
from application import app, nav_avatar, mail
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import datetime
import re
from application.helpers import login_required
from application import db
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
































        







""" -------------------------------------------------------------------------------- """



