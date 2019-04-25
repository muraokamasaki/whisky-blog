from flask import render_template, flash, redirect, url_for, request, abort, g, current_app, session, jsonify
from flask_login import current_user, login_required

from app import db
from app.models import User, Review, Whisky, Distillery, Tag
from app.main import bp
from app.main.forms import EditProfileForm, ReviewForm, AddWhiskyForm, AddDistilleryForm, EditWhiskyForm, \
    EditDistilleryForm
from app.main.info import all_tags


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


"""Routes for user profile"""


@bp.route('/user/<username>')
@login_required
def user(username):
    usr = User.query.filter_by(username=username).first_or_404()
    all_whisky = usr.get_whiskies_listed()
    return render_template('user.html', user=usr, all_whisky=all_whisky)


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


"""Routes for whiskies and reviews"""


@bp.route('/whisky/<id>')
def whisky(id):
    wsk = Whisky.query.filter_by(id=id).first_or_404()
    page = request.args.get('page', 1, type=int)
    reviews = Review.query.filter_by(whisky_id=wsk.id).order_by(Review.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.whisky', id=id, page=reviews.next_num) if reviews.has_next else None
    prev_url = url_for('main.whisky', id=id, page=reviews.prev_num) if reviews.has_prev else None
    return render_template('whisky.html', title=wsk.distillery.name + ' ' + wsk.name,
                           whisky=wsk, reviews=reviews.items, next_url=next_url, prev_url=prev_url)


@bp.route('/edit_whisky/<id>', methods=['GET', 'POST'])
@login_required
def edit_whisky(id):
    wsk = Whisky.query.filter_by(id=id).first_or_404()
    form = EditWhiskyForm(name=wsk.name, distillery=wsk.distillery)
    if form.validate_on_submit():
        wsk.name = form.name.data
        wsk.about = form.about.data
        db.session.commit()
        flash('Updated')
        return redirect(url_for('main.whisky', id=id))
    elif request.method == 'GET':
        form.name.data = wsk.name
        form.about.data = wsk.about
    return render_template('edit_form.html', title='Edit whisky', form=form, whisky=wsk)


@bp.route('/whisky/<id>/submit', methods=['GET', 'POST'])
@login_required
def submit_review(id):
    wsk = Whisky.query.filter_by(id=id).first_or_404()
    form = ReviewForm()
    t = [[x[0] for x in all_tags[i*4:(i*4)+4]] for i in range(len(all_tags) // 4 + 1)]
    if form.validate_on_submit():
        review = Review(nose=form.nose.data, palate=form.palate.data, finish=form.finish.data,
                        score=form.score.data, author=current_user, whisky=wsk)
        db.session.add(review)
        db.session.commit()
        for tag in list(form.add_tags.data):
            review.add_tag(Tag.query.filter_by(name=tag).first())
        db.session.commit()
        flash('Your review has been submitted')
        return redirect(url_for('main.whisky', id=wsk.id))
    return render_template('submit_review.html', form=form, whisky=wsk, all_tags=t)


@bp.route('/edit_review/<rev_id>', methods=['GET', 'POST'])
@login_required
def edit_review(rev_id):
    rev = Review.query.filter_by(id=rev_id).first_or_404()
    wsk = Whisky.query.filter_by(id=rev.whisky_id).first()
    if rev.author.id is not current_user.id:
        abort(403)
    form = ReviewForm()
    t = [[x[0] for x in all_tags[i * 4:(i * 4) + 4]] for i in range(len(all_tags) // 4 + 1)]
    if form.validate_on_submit():
        rev.nose = form.nose.data
        rev.palate = form.palate.data
        rev.finish = form.finish.data
        rev.score = form.score.data
        for tag in list(form.add_tags.data):
            rev.add_tag(Tag.query.filter_by(name=tag).first())
        db.session.commit()
        flash('Your review has been edited')
        return redirect(url_for('main.whisky', id=wsk.id))
    elif request.method == 'GET':
        form.nose.data = rev.nose
        form.palate.data = rev.palate
        form.finish.data = rev.finish
        form.score.data = rev.score
        form.checked_tags = {t.name for t in rev.get_tags()}
    return render_template('submit_review.html', form=form, whisky=wsk, all_tags=t)


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


@bp.route('/whisky_list')
def whisky_list():
    all_distillery = list(Distillery.query.order_by(Distillery.name.asc()).all())
    return render_template('whisky_list.html', title='All distilleries', all_distillery=all_distillery)


@bp.route('/whisky/<id>/popup')
@login_required
def whisky_popup(id):
    wsk = Whisky.query.filter_by(id=id).first_or_404()
    if wsk.number_reviews() == 1:
        msg = 'There is 1 review.'
    elif wsk.number_reviews() == 0:
        msg = 'There are no reviews.'
    else:
        msg = f'There are {wsk.number_reviews()} reviews.'
    return jsonify(message=msg)


@bp.route('/whisky/<id>/tried')
@login_required
def whisky_tried(id):
    wsk = Whisky.query.filter_by(id=id).first_or_404()
    if not current_user.has_whisky(wsk):
        current_user.add_whisky(wsk)
    else:
        current_user.remove_whisky(wsk)
    db.session.commit()
    return redirect(url_for('main.whisky', id=wsk.id))


"""Routes for distilleries"""


@bp.route('/distillery/<id>')
def distillery(id):
    dist = Distillery.query.filter_by(id=id).first_or_404()
    return render_template('distillery.html', title=dist.name, distillery=dist)


@bp.route('/distillery/<id>/add_whisky', methods=['GET', 'POST'])
def add_whisky(id):
    dist = Distillery.query.filter_by(id=id).first_or_404()
    form = AddWhiskyForm(distillery=dist)
    if form.validate_on_submit():
        if form.about.data:
            wsk = Whisky(name=form.name.data, about=form.about.data, distillery=dist)
        else:
            wsk = Whisky(name=form.name.data, distillery=dist)
        db.session.add(wsk)
        db.session.commit()
        return redirect(url_for('main.distillery', id=id))
    return render_template('add_whisky.html', distillery=dist, form=form)


@bp.route('/add_distillery', methods=['GET', 'POST'])
@login_required
def add_distillery():
    form = AddDistilleryForm()
    if form.validate_on_submit():
        dist = Distillery(name=form.name.data.title(), location=form.region.data)
        db.session.add(dist)
        db.session.commit()
        flash('Distillery added')
        return redirect(url_for('main.distillery', id=dist.id))
    return render_template('add_distillery.html', title='Add distillery', form=form)


@bp.route('/edit_distillery/<id>', methods=['GET', 'POST'])
@login_required
def edit_distillery(id):
    dist = Distillery.query.filter_by(id=id).first_or_404()
    form = EditDistilleryForm(dist.name)
    if form.validate_on_submit():
        dist.name = form.name.data
        dist.location = form.region.data
        dist.owner = form.owner.data
        dist.founded = form.founded.data
        db.session.commit()
        flash('Updated')
        return redirect(url_for('main.distillery', id=id))
    elif request.method == 'GET':
        form.name.data = dist.name
        form.region.data = dist.location
        form.owner.data = dist.owner
        form.founded.data = dist.founded
    return render_template('edit_form.html', title='Edit distillery', form=form, distillery=dist)


"""Routes for miscellaneous"""


@bp.route('/recipes')
@login_required
def recipe_page():
    return render_template('recipe_page.html')


@bp.route('/language/<language>')
def set_language(language=None):
    session['language'] = language
    return redirect(url_for('main.home'))
