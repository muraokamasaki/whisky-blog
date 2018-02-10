from flask import render_template, url_for, flash, redirect, request, abort
from flask_login import current_user, login_required
from app import db, current_app
from app.models import User, Review, Whisky, Distillery, Tag
from app.main import bp
from app.main.forms import EditProfileForm, ReviewForm, AddWhiskyForm, AddDistilleryForm, EditWhiskyForm, \
    EditDistilleryForm, all_tags


@bp.route('/')
@bp.route('/home')
def home():
    return render_template('home.html')


@bp.route('/explore')
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Review.query.order_by(Review.timestamp.desc()).paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('explore.html', title='Explore', reviews=posts.items, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your profile has been updated!')
        return redirect(url_for('main.user', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_form.html', title='Edit Profile', form=form, profile=True)


@bp.route('/whisky/<id>', methods=['GET', 'POST'])
def whisky(id):
    whisky = Whisky.query.filter_by(id=id).first_or_404()
    form = ReviewForm()
    t = []
    for i in range(len(all_tags) // 4 + 1):
        a = []
        for j in range(4):
            try:
                a.append(all_tags[i * 4 + j][0])
            except:
                break
        t.append(a)
    if form.validate_on_submit():
        review = Review(body=form.review.data, author=current_user, whisky=whisky)
        db.session.add(review)
        db.session.commit()
        for tag in list(form.add_tags.data):
            review.add_tag(Tag.query.filter_by(name=tag).first())
        db.session.commit()
        flash('Your review has been submitted')
        return redirect(url_for('main.whisky', id=whisky.id))
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.filter_by(whisky_id=whisky.id).order_by(Review.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.whisky', id=id, page=reviews.next_num) if reviews.has_next else None
    prev_url = url_for('main.whisky', id=id, page=reviews.prev_num) if reviews.has_prev else None
    return render_template('whisky.html', title=whisky.distillery.name + ' ' + whisky.name, all_tags=t,
                           whisky=whisky, reviews=reviews.items, form=form, next_url=next_url, prev_url=prev_url)


@bp.route('/delete/<post_id>')
@login_required
def delete_post(post_id):
    post = Review.query.filter_by(id=post_id).first_or_404()
    if post.author.id is not current_user.id:
        abort(403)
    whisky_page = post.whisky_id
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('main.whisky', id=whisky_page))


@bp.route('/distillery/<id>', methods=['GET', 'POST'])
def distillery(id):
    distillery = Distillery.query.filter_by(id=id).first_or_404()
    form = AddWhiskyForm(distillery=distillery)
    if form.validate_on_submit():
        if form.about.data:
            whisky = Whisky(name=form.name.data, about=form.about.data, distillery=distillery)
        else:
            whisky = Whisky(name=form.name.data, distillery=distillery)
        db.session.add(whisky)
        db.session.commit()
        return redirect(url_for('main.distillery', id=id))
    return render_template('distillery.html', title=distillery.name, distillery=distillery, form=form)


@bp.route('/whisky_list')
def whisky_list():
    all_distillery = list(Distillery.query.order_by(Distillery.name.asc()).all())
    return render_template('whisky_list.html', title='All distilleries', all_distillery=all_distillery)


@bp.route('/add_distillery', methods=['GET', 'POST'])
@login_required
def add_distillery():
    form = AddDistilleryForm()
    if form.validate_on_submit():
        distillery = Distillery(name=form.name.data.title(), location=form.region.data)
        db.session.add(distillery)
        db.session.commit()
        flash('Distillery added')
        return redirect(url_for('main.distillery',id=distillery.id))
    return render_template('add_distillery.html', title='Add distillery', form=form)


@bp.route('/edit_distillery/<id>', methods=['GET', 'POST'])
@login_required
def edit_distillery(id):
    distillery = Distillery.query.filter_by(id=id).first_or_404()
    form = EditDistilleryForm(distillery.name)
    if form.validate_on_submit():
        distillery.name = form.name.data
        distillery.location = form.region.data
        db.session.commit()
        flash('Updated')
        return redirect(url_for('main.distillery', id=id))
    elif request.method == 'GET':
        form.name.data = distillery.name
        form.region.data = distillery.location
    return render_template('edit_form.html', title='Edit distillery', form=form, distillery=distillery)


@bp.route('/edit_whisky/<id>', methods=['GET', 'POST'])
@login_required
def edit_whisky(id):
    whisky = Whisky.query.filter_by(id=id).first_or_404()
    form = EditWhiskyForm(name=whisky.name, distillery=whisky.distillery)
    if form.validate_on_submit():
        whisky.name = form.name.data
        whisky.about = form.about.data
        db.session.commit()
        flash('Updated')
        return redirect(url_for('main.whisky', id=id))
    elif request.method == 'GET':
        form.name.data = whisky.name
        form.about.data = whisky.about
    return render_template('edit_form.html', title='Edit whisky', form=form, whisky=whisky)


@bp.route('/whisky/<id>/popup')
@login_required
def whisky_popup(id):
    whisky = Whisky.query.filter_by(id=id).first_or_404()
    return render_template('whisky_popup.html', whisky=whisky)
