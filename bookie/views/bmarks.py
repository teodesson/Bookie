"""Controllers related to viewing lists of bookmarks"""
import logging

from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.view import view_config

from bookie.bcelery import tasks
from bookie.lib.access import ReqAuthorize
from bookie.lib.utils import (
    suggest_tags,
    url_fix)
from bookie.lib.urlhash import generate_hash
from bookie.models import (
    Bmark,
    BmarkMgr,
    DBSession,
    InvalidBookmark,
    TagMgr,
)
from bookie.views import api

LOG = logging.getLogger(__name__)
RESULTS_MAX = 50


@view_config(
    route_name="bmark_recent",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="bmark_recent_tags",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="user_bmark_recent",
    renderer="/bmark/recent.mako")
@view_config(
    route_name="user_bmark_recent_tags",
    renderer="/bmark/recent.mako")
def recent(request):
    """Testing a JS driven ui with backbone/etc"""
    rdict = request.matchdict
    params = request.params

    # Make sure we generate a url to feed our rss link.
    current_route = request.current_route_url()

    # check for auth related stuff
    # are we looking for a specific user
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    # do we have any tags to filter upon
    tags = rdict.get('tags', None)

    if isinstance(tags, str):
        tags = [tags]

    ret = {
        'username': username,
        'tags': tags,
        'rss_url': current_route.replace('recent', 'rss')
    }

    # if we've got url parameters for the page/count then use those to help
    # feed the init of the ajax script
    ret['count'] = params.get('count') if 'count' in params else RESULTS_MAX
    ret['page'] = params.get('page') if 'page' in params else 0

    # Do we have any sorting criteria?
    ret['sort'] = params.get('sort') if 'sort' in params else None

    return ret


@view_config(
    route_name="bmark_recent_rss",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="bmark_recent_rss_tags",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="user_bmark_rss",
    renderer="/bmark/rss.mako")
@view_config(
    route_name="user_bmark_rss_tags",
    renderer="/bmark/rss.mako")
def recent_rss(request):
    rdict = request.matchdict
    request.response.content_type = 'application/atom+xml; charset=UTF-8'

    tags = rdict.get('tags', None)
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    ret = api.bmark_recent(request, with_content=True)
    ret['username'] = username
    ret['tags'] = tags
    return ret


@view_config(
    route_name="user_bmark_edit",
    renderer="/bmark/edit.mako")
@view_config(
    route_name="user_bmark_new",
    renderer="/bmark/edit.mako")
def edit(request):
    """Manual add a bookmark to the user account

    Can pass in params (say from a magic bookmarklet later)
    url
    description
    extended
    tags

    """
    rdict = request.matchdict
    params = request.params
    url = params.get('url', "")
    title = params.get('description', None)
    new = False
    MAX_TAGS = 10
    tag_suggest = []
    base_tags = set()

    with ReqAuthorize(request, username=rdict['username'].lower()):

        if 'hash_id' in rdict:
            hash_id = rdict['hash_id']
        elif 'hash_id' in params:
            hash_id = params['hash_id']
        else:
            hash_id = None

        if hash_id:
            bmark = BmarkMgr.get_by_hash(hash_id, request.user.username)
            if bmark is None:
                return HTTPNotFound()
            else:
                title = bmark.description
                url = bmark.hashed.url
        else:
            # Hash the url and make sure that it doesn't exist
            if url != "":
                new_url_hash = generate_hash(url)

                test_exists = BmarkMgr.get_by_hash(
                    new_url_hash,
                    request.user.username)

                if test_exists:
                    location = request.route_url(
                        'user_bmark_edit',
                        hash_id=new_url_hash,
                        username=request.user.username)
                    return HTTPFound(location)

            # No url info given so shown the form to the user.
            new = True
            # Setup a dummy bookmark so the template can operate
            # correctly.
            bmark = Bmark(url, request.user.username, desc=title)

        # Title and url will be in params for new bookmark and
        # fetched from database if it is an edit request
        if title or url:
            suggested_tags = suggest_tags(url)
            suggested_tags.update(suggest_tags(title))
            base_tags.update(suggested_tags)

        # If user is editing a bookmark, suggested tags will include tags
        # based on readable content also
        if not new:
            tag_suggest = TagMgr.suggestions(
                bmark=bmark,
                url=bmark.hashed.url,
                username=request.user.username
            )
        # tags based on url and title will always be there
        # order of tags is important so convert set to list
        tag_suggest.extend(list(base_tags))
        tag_suggest = (tag_suggest[0:MAX_TAGS],
                       tag_suggest)[len(tag_suggest) < MAX_TAGS]
        return {
            'new': new,
            'bmark': bmark,
            'user': request.user,
            'tag_suggest': list(set(tag_suggest)),
        }


@view_config(route_name="user_bmark_edit_error", renderer="/bmark/edit.mako")
@view_config(route_name="user_bmark_new_error", renderer="/bmark/edit.mako")
def edit_error(request):
    rdict = request.matchdict
    params = request.params
    post = request.POST

    with ReqAuthorize(request, username=rdict['username'].lower()):
        if 'is_private' in post:
            post['is_private'] = True
        else:
            post['is_private'] = False
        if 'new' in request.url:
            try:
                try:
                    bmark = BmarkMgr.get_by_url(
                        post['url'],
                        username=request.user.username)
                except Exception as exc:
                    LOG.error(exc)
                    bmark = None
                if bmark:
                    return {
                        'new': False,
                        'bmark': bmark,
                        'message': "URL already Exists",
                        'user': request.user,
                    }
                else:
                    bmark = BmarkMgr.store(
                        url=url_fix(post['url']),
                        username=request.user.username,
                        desc=post['description'],
                        ext=post['extended'],
                        tags=post['tags'],
                        is_private=post['is_private'])

                    # Assign a task to fetch this pages content and parse it
                    # out for storage and indexing.
                    DBSession.flush()
                    tasks.fetch_bmark_content.delay(bmark.bid)

            except InvalidBookmark as exc:
                # There was an issue using the supplied data to create a new
                # bookmark. Send the data back to the user with the error
                # message.
                bmark = Bmark(
                    post['url'],
                    request.user.username,
                    desc=post['description'],
                    ext=post['extended'],
                    tags=post['tags'],
                    is_private=post['is_private'])

                return {
                    'new': True,
                    'bmark': bmark,
                    'message': str(exc),
                    'user': request.user,
                }

        else:
            if 'hash_id' in rdict:
                hash_id = rdict['hash_id']
            elif 'hash_id' in params:
                hash_id = params['hash_id']

            bmark = BmarkMgr.get_by_hash(hash_id, request.user.username)
            if bmark is None:
                return HTTPNotFound()

            bmark.fromdict(post)
            bmark.update_tags(post['tags'])

        # if this is a new bookmark from a url, offer to go back to that url
        # for the user.
        if 'go_back' in params and params['comes_from'] != "":
            return HTTPFound(location=params['comes_from'])
        else:
            return HTTPFound(
                location=request.route_url('user_bmark_recent',
                                           username=request.user.username))


@view_config(
    route_name="bmark_readable",
    renderer="/bmark/readable.mako")
def readable(request):
    """Display a readable version of this url if we can"""
    rdict = request.matchdict
    bid = rdict.get('hash_id', None)
    username = rdict.get('username', None)
    if username:
        username = username.lower()

    if bid:
        found = BmarkMgr.get_by_hash(bid, username=username)
        if found:
            return {
                'bmark': found,
                'username': username,
            }
        else:
            return HTTPNotFound()


@view_config(route_name="user_delete_all_bookmarks",
             renderer="/accounts/index.mako")
def delete_all_bookmarks(request):
    """Delete all bookmarks of the current user"""
    rdict = request.matchdict
    post = request.POST
    with ReqAuthorize(request, username=rdict['username'].lower()):
        username = request.user.username
        if username:
            if post['delete'] == 'Delete':
                from bookie.bcelery import tasks
                tasks.delete_all_bookmarks.delay(username)
                return {
                    'user': request.user,
                    'message': 'The delete request has been queued' +
                               ' and will be acted upon shortly.',
                }
            else:
                return {
                    'user': request.user,
                    'message': 'Delete request not confirmed. ' +
                               'Please make sure to enter' +
                               ' \'Delete\' to confirm.',
                }
        else:
            return HTTPNotFound()
