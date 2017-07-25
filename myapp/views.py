# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from django.shortcuts import render, redirect
from forms import SignUpForm, LoginForm, PostForm, LikeForm, CommentForm
from models import UserModel, SessionToken, PostModel, LikeModel, CommentModel ,CategoryModel
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from django.utils import timezone
from clarifai.rest import ClarifaiApp
from intrest.settings import BASE_DIR
from imgurpython import ImgurClient
import ctypes

import sendgrid
from sendgrid.helpers.mail import *


clarafai_api_key='cd9af066bd5b48bb867c581bb57b7ca7'

IMGUR_CLIENT_ID = "9c9bf0c17f4ac16"
IMGUR_CLIENT_SECRET = "cd2f3f14d28677368f0c26ee558ff6841e6e098a"

#no key.
sendgrid_key = ""


# Create your views here.
def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # saving data to DB
            user = UserModel(name=name, password=make_password(password), email=email, username=username)
            user.save()

            sg = sendgrid.SendGridAPIClient(apikey=(sendgrid_key))
            from_email = Email("alamdeep.1@gmail.com")
            to_email = Email(form.cleaned_data['email'])
            subject = "Welcome to SwacchBharat"
            content = Content("text/plain",
                              "Swacch Bharat team welcomes you!\n We hope you like sharing the images of your surroundings to help us build a cleaner india /n")
            mail = Mail(from_email, subject, to_email, content)
            response = sg.client.mail.send.post(request_body=mail.get())
            print(response.status_code)
            print(response.body)
            print(response.headers)

            return render(request, 'success.html')
            # return redirect('login/')
    else:
        form = SignUpForm()

    return render(request, 'index.html', {'form': form})



#make user login
def login_view(request):
    response_data = {}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = UserModel.objects.filter(username=username).first()

            if user:
                if check_password(password, user.password):
                    token = SessionToken(user=user)
                    token.create_token()
                    token.save()
                    response = redirect('feed/')
                    response.set_cookie(key='session_token', value=token.session_token)
                    return response
                else:
                    ctypes.windll.user32.MessageBoxW(0, u"Wrong Password!", u"Error", 0)
                    response_data['message'] = 'Please try again!'
            else:
                ctypes.windll.user32.MessageBoxW(0, u"Invalid Credentials!", u"Error", 0)
                response_data['message'] = 'Please try again!'
        else:
            ctypes.windll.user32.MessageBoxW(0, u"Invalid Credentials!", u"Error", 0)


    elif request.method == 'GET':
        form = LoginForm()

    response_data['form'] = form
    return render(request, 'login.html', response_data)



# Controller for adding a new category.
def add_category(post):
    app = ClarifaiApp(api_key=clarafai_api_key)
    model = app.models.get("general-v1.3")
    response = model.predict_by_url(url=post.image_url)

    if response["status"]["code"] == 10000:
        if response["outputs"]:
            if response["outputs"][0]["data"]:
                if response["outputs"][0]["data"]["concepts"]:
                    for index in range(0, len(response["outputs"][0]["data"]["concepts"])):
                        category = CategoryModel(post=post, category_text = response["outputs"][0]["data"]["concepts"][index]["name"])
                        category.save()
                else:
                    print "No Concepts List Error"
            else:
                print "No Data List Error"
        else:
            print "No Outputs List Error"
    else:
        print "Response Code Error"



#creating new posts
def post_view(request):
    user = check_validation(request)

    if user:
        if request.method == 'POST':
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data.get('image')
                caption = form.cleaned_data.get('caption')
                post = PostModel(user=user, image=image, caption=caption)
                post.save()

                path = str(BASE_DIR + post.image.url)

                client = ImgurClient( IMGUR_CLIENT_ID,IMGUR_CLIENT_SECRET)
                post.image_url = client.upload_from_path(path, anon=True)['link']
                post.save()

                add_category(post)

                return redirect('/feed/')


        else:
            form = PostForm()
        return render(request, 'post.html', {'form': form})
    else:
        return redirect('/login/')



#redirecting the user to news feed once he logs in.
def feed_view(request):
    user = check_validation(request)
    if user:

        posts = PostModel.objects.all().order_by('-created_on')

        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True

        return render(request, 'feed.html', {'posts': posts})
    else:

        return redirect('/login/')



#for posting like.
def like_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = LikeForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            existing_like = LikeModel.objects.filter(post_id=post_id, user=user).first()
            if not existing_like:
                like = LikeModel.objects.create(post_id=post_id, user=user)

                sg = sendgrid.SendGridAPIClient(apikey=(sendgrid_key))
                from_email = Email("alamdeep.1@gmail.com")
                to_email = Email(like.post.user.email)
                subject = "You have a new like on your post %d " % (post_id)
                content = Content("text/plain",
                                  "You have a new like on your post %d /n Login to view the details" % post_id)
                mail = Mail(from_email, subject, to_email, content)
                response = sg.client.mail.send.post(request_body=mail.get())
                print(response.status_code)
                print(response.body)
                print(response.headers)

            else:
                existing_like.delete()
            return redirect('/feed/')
    else:
        return redirect('/login/')



#for making a comment.
def comment_view(request):
    user = check_validation(request)
    if user and request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            post_id = form.cleaned_data.get('post').id
            comment_text = form.cleaned_data.get('comment_text')
            comment = CommentModel.objects.create(user=user, post_id=post_id, comment_text=comment_text)
            comment.save()

            sg = sendgrid.SendGridAPIClient(apikey=(sendgrid_key))
            from_email = Email("alamdeep.1@gmail.com")
            to_email = Email(comment.post.user.email)
            subject = "Welcome to Swacch Bharat"
            content = Content("text/plain",
                              "Swacch Bharat team welcomes you!\n We hope you like sharing the images of your surroundings to help us build a cleaner india/n")
            mail = Mail(from_email, subject, to_email, content)
            response = sg.client.mail.send.post(request_body=mail.get())
            print(response.status_code)
            print(response.body)
            print(response.headers)

            return redirect('/feed/')
        else:
            return redirect('/feed/')
    else:
        return redirect('/login')



# For validating the session
def check_validation(request):
    if request.COOKIES.get('session_token'):
        session = SessionToken.objects.filter(session_token=request.COOKIES.get('session_token')).first()
        if session:
            time_to_live = session.created_on + timedelta(days=2)
            if time_to_live > timezone.now():
                return session.user
    else:
        return None



def new(request):
    user = check_validation(request)
    if user:

        posts = PostModel.objects.all().order_by('-created_on')

        for post in posts:
            existing_like = LikeModel.objects.filter(post_id=post.id, user=user).first()
            if existing_like:
                post.has_liked = True

        return render(request, 'new.html', {'posts': posts})
    else:

        return redirect('/login/')




#logout  (deleting session).
def logout_view(request):
    request.session.modified = True
    response = redirect("/login/")
    response.delete_cookie(key="session_token")
    return response




def posts_of_particular_user(request,user_name):
    user = check_validation(request)
    if user:
        posts=PostModel.objects.all().filter(user__username=user_name)
        return render(request,'postofuser.html',{'posts':posts,'user_name':user_name})
    else:
        return redirect('/login/')